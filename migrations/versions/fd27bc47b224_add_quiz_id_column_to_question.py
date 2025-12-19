"""add quiz_id column to question

Revision ID: fd27bc47b224
Revises: 7c3c6e021991
Create Date: 2025-11-13 21:16:49.739077
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fd27bc47b224'
down_revision = '7c3c6e021991'
branch_labels = None
depends_on = None


def upgrade():
    # Tambah kolom quiz_id
    with op.batch_alter_table('question', schema=None) as batch_op:
        batch_op.add_column(sa.Column('quiz_id', sa.Integer(), nullable=True))  # sementara nullable dulu
        batch_op.alter_column(
            'image_filename',
            existing_type=sa.VARCHAR(length=200),
            type_=sa.String(length=255),
            existing_nullable=True
        )
        batch_op.create_foreign_key(
            'fk_question_quiz_id',  # ✅ nama constraint wajib ada
            'quiz',
            ['quiz_id'],
            ['id']
        )

    # Isi default quiz_id biar gak null (opsional, tergantung data kamu)
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE question SET quiz_id = 1 WHERE quiz_id IS NULL"))

    # Baru ubah jadi NOT NULL
    with op.batch_alter_table('question', schema=None) as batch_op:
        batch_op.alter_column('quiz_id', nullable=False)


def downgrade():
    # Hapus kolom & constraint
    with op.batch_alter_table('question', schema=None) as batch_op:
        batch_op.drop_constraint('fk_question_quiz_id', type_='foreignkey')
        batch_op.alter_column(
            'image_filename',
            existing_type=sa.String(length=255),
            type_=sa.VARCHAR(length=200),
            existing_nullable=True
        )
        batch_op.drop_column('quiz_id')
