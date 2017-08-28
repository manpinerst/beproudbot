import logging
import os

import requests
from slackbot.bot import listen_to

from db import Session
from utils.slack import get_user_name

from .redmine_models import RedmineUser, ProjectChannel

logging = logging.getLogger(__name__)
REDMINE_URL = os.environ.get("REDMINE_URL", "https://project.beproud.jp/redmine/issues/")

USER_NOT_FOUND = '{}はRedmineUserテーブルに登録されていません。'
TICKET_INFO = '{}\n{}'
NO_PERMISSIONS = '{}は{}で表示できません。'


@listen_to('[t](\d+)')
def show_ticket_information(message, ticket_id):
    """Redmineのチケット情報を参照する.

    :param message: slackbotの各種パラメータを保持したclass
    :param ticket_id: redmineのチケット番号
    """
    s = Session()

    channel = message.channel
    channel_id = channel._body['id']
    user_id = message.body['user']

    user = s.query(RedmineUser).filter(RedmineUser.user_id == user_id).one_or_none()

    if not user:
        user_name = get_user_name(user_id)
        message.send(USER_NOT_FOUND.format(user_name))
        return

    ticket_url = "{}/{}".format(REDMINE_URL, ticket_id)
    headers = {'X-Redmine-API-Key': user.api_key}
    res = requests.get("{}.json".format(ticket_url), headers=headers)

    if res.status_code != 200:
        user_name = get_user_name(user_id)
        logging.info("{} doesn't have access to ticket #{}".format(user_name, ticket_id))
        return

    ticket = res.json()
    proj_id = ticket["issue"]["project"]["id"]
    proj_room = s.query(ProjectChannel).filter(ProjectChannel.project_id == proj_id).first()

    if proj_room and channel_id in proj_room.channels.split(","):
        message.send(TICKET_INFO.format(ticket["issue"]["subject"], ticket_url))
    else:
        message.send(NO_PERMISSIONS.format(ticket_id, channel._body['name']))
