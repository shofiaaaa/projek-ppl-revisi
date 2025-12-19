"""fix quiz model

Revision ID: 14b8b0fb30d5
Revises: 778945dd8f3e
Create Date: 2025-11-13 14:44:18.126154
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '14b8b0fb30d5'
down_revision = '778945dd8f3e'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # ✅ Cek apakah tabel quiz_question sudah ada
    if 'quiz_question' not in inspector.get_table_names():
        op.create_table(
            'quiz_question',
            sa.Column('quiz_id', sa.Integer(), nullable=True),
            sa.Column('question_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['question_id'], ['question.id']),
            sa.ForeignKeyConstraint(['quiz_id'], ['quiz.id'])
        )
        print("✅ Tabel 'quiz_question' dibuat.")
    else:
        print("⚠️  Tabel 'quiz_question' sudah ada — dilewati.")

    # ✅ Hapus kolom quiz_id dari question kalau memang ada
    columns = [col['name'] for col in inspector.get_columns('question')]
    if 'quiz_id' in columns:
        fks = inspector.get_foreign_keys('question')
        with op.batch_alter_table('question', schema=None) as batch_op:
            found_fk = False
            for fk in fks:
                if fk.get('referred_table') == 'quiz':
                    fk_name = fk.get('name')
                    if fk_name:
                        print(f"🗑️ Menghapus constraint: {fk_name}")
                        batch_op.drop_constraint(fk_name, type_='foreignkey')
                        found_fk = True
                    else:
                        print("⚠️ Constraint foreign key tidak punya nama, dilewati.")
            if not found_fk:
                print("⚠️ Tidak ditemukan FK langsung ke quiz, lanjut hapus kolom saja.")
            batch_op.drop_column('quiz_id')
            print("🗑️ Kolom 'quiz_id' dihapus.")

    # ✅ Tambah kolom baru di quiz kalau belum ada
    quiz_columns = [col['name'] for col in inspector.get_columns('quiz')]
    with op.batch_alter_table('quiz', schema=None) as batch_op:
        if 'subject' not in quiz_columns:
            batch_op.add_column(sa.Column('subject', sa.String(length=100), nullable=True))
            print("✅ Kolom 'subject' ditambahkan.")
        if 'created_at' not in quiz_columns:
            batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))
            print("✅ Kolom 'created_at' ditambahkan.")

def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # ✅ Balikkan kolom di quiz
    with op.batch_alter_table('quiz', schema=None) as batch_op:
        quiz_columns = [col['name'] for col in inspector.get_columns('quiz')]
        if 'created_at' in quiz_columns:
            batch_op.drop_column('created_at')
        if 'subject' in quiz_columns:
            batch_op.drop_column('subject')

    # ✅ Tambahkan kembali quiz_id ke question jika belum ada
    question_columns = [col['name'] for col in inspector.get_columns('question')]
    with op.batch_alter_table('question', schema=None) as batch_op:
        if 'quiz_id' not in question_columns:
            batch_op.add_column(sa.Column('quiz_id', sa.INTEGER(), nullable=True))
            batch_op.create_foreign_key('question_quiz_id_fkey', 'quiz', ['quiz_id'], ['id'])

    # ✅ Drop tabel quiz_question kalau ada
    if 'quiz_question' in inspector.get_table_names():
        op.drop_table('quiz_question')
