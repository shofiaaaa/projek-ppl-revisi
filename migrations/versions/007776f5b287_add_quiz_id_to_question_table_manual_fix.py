"""add quiz_id to question table (manual fix)

Revision ID: 007776f5b287
Revises: fd27bc47b224
Create Date: 2025-11-14 02:57:11.305543

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007776f5b287'
down_revision = 'fd27bc47b224'
branch_labels = None
depends_on = None


def upgrade():
    # Tambahkan kolom quiz_id jika belum ada
    with op.batch_alter_table('question', schema=None) as batch_op:
        batch_op.add_column(sa.Column('quiz_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_question_quiz_id', 'quiz', ['quiz_id'], ['id'])


def downgrade():
    # Hapus kolom quiz_id
    with op.batch_alter_table('question', schema=None) as batch_op:
        batch_op.drop_constraint('fk_question_quiz_id', type_='foreignkey')
        batch_op.drop_column('quiz_id')
