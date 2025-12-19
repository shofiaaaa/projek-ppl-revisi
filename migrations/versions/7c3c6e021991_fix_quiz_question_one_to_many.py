"""fix quiz-question one-to-many

Revision ID: 7c3c6e021991
Revises: 14b8b0fb30d5
Create Date: 2025-11-13 16:53:12.490727

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c3c6e021991'
down_revision = '14b8b0fb30d5'
branch_labels = None
depends_on = None


def upgrade():
    # Dapatkan koneksi aktif
    conn = op.get_bind()

    # Cek apakah tabel quiz_question ada sebelum drop
    inspector = sa.inspect(conn)
    if 'quiz_question' in inspector.get_table_names():
        op.drop_table('quiz_question')

    # Tambahkan kolom quiz_id ke tabel question (jika belum ada)
    with op.batch_alter_table('question', schema=None) as batch_op:
        existing_columns = [col['name'] for col in inspector.get_columns('question')]
        if 'quiz_id' not in existing_columns:
            batch_op.add_column(sa.Column('quiz_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key('fk_question_quiz_id', 'quiz', ['quiz_id'], ['id'])


    # ### end Alembic commands ###


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Ambil semua kolom question kecuali quiz_id
    columns = [col['name'] for col in inspector.get_columns('question')]
    if 'quiz_id' in columns:
        columns.remove('quiz_id')

    # Backup data lama (tanpa quiz_id)
    question_data = conn.execute(sa.text(f"SELECT {', '.join(columns)} FROM question")).fetchall()

    # Rename tabel lama
    op.rename_table('question', 'question_old')

    # Buat ulang tabel tanpa kolom quiz_id
    op.create_table(
        'question',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('text', sa.String(length=255), nullable=False),
        sa.Column('image_filename', sa.String(length=255), nullable=True)
        # tambahkan kolom lain di sini kalau ada (selain quiz_id)
    )

    # Salin kembali data lama
    for row in question_data:
        conn.execute(
            sa.text(
                f"INSERT INTO question ({', '.join(columns)}) VALUES ({', '.join([':' + c for c in columns])})"
            ),
            dict(zip(columns, row))
        )

    # Hapus tabel lama
    op.drop_table('question_old')

    # Buat ulang tabel quiz_question
    op.create_table(
        'quiz_question',
        sa.Column('quiz_id', sa.Integer, nullable=True),
        sa.Column('question_id', sa.Integer, nullable=True),
        sa.ForeignKeyConstraint(['quiz_id'], ['quiz.id']),
        sa.ForeignKeyConstraint(['question_id'], ['question.id'])
    )

