"""
スクリプト概要
~~~~~~~~~~
systemdでtimerを作成し、定期的に実行するPython
1,Redmineから期限切れ、期限切れそうなチケットを取得する
2,チケットの期限によって分類
3,各チャンネルに期限切れ、期限が切れそうなチケットの情報を通知する。
"""

from redminelib import Redmine
from datetime import timedelta, date
from slackclient import SlackClient
import argparse
from textwrap import dedent
from configparser import ConfigParser, NoSectionError

from haro.plugins.redmine_models import ProjectChannel

from db import init_dbsession

from slackbot_settings import (
    REDMINE_URL,
    API_KEY,
    SLACK_API_TOKEN,
    SQLALCHEMY_URL,
    SQLALCHEMY_ECHO,
    SQLALCHEMY_POOL_SIZE,
)

from db import Session

LIMIT = 7 # 期限が1週間以内のチケットを分別するために使用

def get_ticket_information():
    """Redmineのチケット情報とチケットと結びついているSlackチャンネルを取得
    """
    redmine = Redmine(REDMINE_URL, key=API_KEY)
    # すべてのチケットを取得
    issues = redmine.issue.all(sort='subject:desc')

    projects_past_due_date = {}
    projects_close_to_due_date = {}
    s = Session()
    for issue in issues:
        # due_date属性とdue_dateがnoneの場合は除外
        if not getattr(issue, 'due_date', None):
            continue
        proj_id = issue.project.id
        # issueのデータをSlack通知用にformatする。
        issue_display = display_issue(issue)
        proj_rooms = s.query(ProjectChannel).filter(
            ProjectChannel.project_id == project).all()

        for proj_room in proj_rooms:
            channels = proj_room.channels
            if len(channels) > 0: # only save issues that has slack channel
                # issueの期限が過ぎていた場合
                if is_past_due_date(issue.due_date):
                   # proj_idをkeyにして値にformatしたIssue情報の値を入れる。
                   # 辞書のkeyと値の例:{proj_id: ['- 2017-03-31 23872: サーバーセキュリティーの基準を作ろう(@takanory)'], xxx:['- xxxxxxx']}
                    if proj_id not in projects_past_due_date.keys():
                        projects_past_due_date[proj_id] = [issue_display]
                    else:
                        projects_past_due_date[proj_id].append(issue_display)
                # issueの期限が1週間以内の場合
                elif is_close_to_due_date(issue.due_date):
                    if proj_id not in projects_close_to_due_date.keys():
                         projects_close_to_due_date[proj_id] = [issue_display]
                    else:
                         projects_close_to_due_date[proj_id].append(issue_display)
                else:
                    continue

    # 各プロジェクトのチケット通知をSlackチャンネルに送る。
    send_ticket_info_to_channels(projects_past_due_date, 0)
    send_ticket_info_to_channels(projects_close_to_due_date, 1)


def display_issue(issue):
    """issueの詳細をSlackに表示用にフォーマットする。

    フォーマット例:
    - 2017-03-31 23872: サーバーセキュリティーの基準を作ろう(@takanory)
    :param issue: redmineのissue
    """

    return '{} {} {}: {} (@{})'.format('-', issue.due_date, issue.id, issue.subject, issue.author)


def is_past_due_date(due_date):
    """期限切れたチケットをチェックするFunction
    期限が切れていたらTrueを返す。それ以外はFalse

    :param due_date: 各チケットのdue_date
    """
    today = date.today()

    return due_date < today


def is_close_to_due_date(due_date):
    """期限が1週間以内に切れそうなチケットをチェックするFunction
    期限が切れていたらTrueを返す。それ以外はFalse

    :param due_date: 各チケットのdue_date
    """
    today = date.today()

    return due_date < today - timedelta(LIMIT)


def send_ticket_info_to_channels(projects, type):
    """チケット情報を各Slackチャンネルごとに通知する。

        :param projects: 期限が切れたプロジェクト、期限が切れそうなプロジェクトのdict
        :param type: int type=0 -> 期限切れ type=1 ->期限切れそうなチケット
    """
    s = Session()
    sc = SlackClient(SLACK_API_TOKEN)
    for project in projects.keys():
        # 各プロジェクトのproj_roomを獲得する。
        proj_rooms = s.query(ProjectChannel).filter(
            ProjectChannel.project_id == project).all()

        # api_call()を使用し、すべてのSlackチャンネルに期限が切れたチケット、期限が切れそうな通知をチケットまとめて送る
        # 1つのredmineプロジェクトが複数のslackチャンネルに関連付けられているケースに対応
        for proj_room in proj_rooms:
            channels = proj_room.channels
            # プロジェクトごとのチケット数カウントを取得
            issue_count = len(projects[project])
            if not type:  # 期限切れチケット
                message = '期限が切れたチケットは' + str(issue_count) + ' 件です\n'
            else:  # 期限切れそうなチケット
                message = 'もうすぐ期限が切れそうなチケットは' + str(issue_count) + ' 件です\n'
            for issue in projects[project]:
                message += display_issue(issue) + '\n'

            for channel in channels:
                sc.api_call(
                    "chat.postMessage",
                    channel=channel,
                    text= message
                )

def get_argparser():

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=dedent('''\
            説明:
            haroの設定ファイルを読み込んだ後にslackbotを起動します'''))

    parser.add_argument('-c', '--config',
                        type=argparse.FileType('r'),
                        default='alembic/conf.ini',
                        help='ini形式のファイルをファイルパスで指定します')

    return parser

def main():
    """設定ファイルをparseして、slackbotを起動します

    1. configparserで設定ファイルを読み込む
    2. 設定ファイルに `alembic` セクションが設定されているかチェック
    3. 設定ファイルの情報でDB周りの設定を初期化
    4. slackbotの処理を開始
    """
    parser = get_argparser()
    args = parser.parse_args()
    conf = ConfigParser()
    conf.read_file(args.config)
    # 環境変数で指定したいため ini ファイルでなくここで追記
    conf["alembic"]['sqlalchemy.url'] = SQLALCHEMY_URL
    conf["alembic"]['sqlalchemy.echo'] = SQLALCHEMY_ECHO
    if SQLALCHEMY_POOL_SIZE:
        conf["alembic"]['sqlalchemy.pool_size'] = '20' #SQLALCHEMY_POOL_SIZE
    if not conf.has_section('alembic'):
        raise NoSectionError('alembic')

    init_dbsession(conf['alembic'])
    get_ticket_information()


if __name__ == "__main__":
    main()

