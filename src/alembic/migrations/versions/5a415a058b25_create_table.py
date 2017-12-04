"""create table

Revision ID: 5a415a058b25
Revises: 919388975e00
Create Date: 2017-12-04 12:05:58.895139

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a415a058b25'
down_revision = '919388975e00'
branch_labels = None
depends_on = None

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('yougo',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('channel_id', sa.Unicode(length=100), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('word', sa.Unicode(length=100), nullable=False),
    sa.Column('english_name', sa.Unicode(length=100), nullable=True),
    sa.Column('data_type', sa.Unicode(length=100), nullable=True),
    sa.Column('coding_name', sa.Unicode(length=100), nullable=True),
    sa.Column('description', sa.UnicodeText(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('yougo')
    # ### end Alembic commands ###
