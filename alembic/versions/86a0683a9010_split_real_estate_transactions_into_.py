"""split real_estate_transactions into sales and rentals

Revision ID: 86a0683a9010
Revises: dd4575e35723
Create Date: 2026-02-15 20:03:59.071354

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '86a0683a9010'
down_revision: Union[str, Sequence[str], None] = 'dd4575e35723'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 기존 DB에 이미 존재하는 enum 타입 참조 (create_type=False)
property_type_enum = postgresql.ENUM(
    'LAND', 'COMMERCIAL', 'DETACHED_HOUSE', 'ROW_HOUSE', 'APARTMENT', 'OFFICETEL',
    name='property_type_enum', create_type=False,
)
transaction_type_enum = postgresql.ENUM(
    'SALE', 'JEONSE', 'MONTHLY_RENT',
    name='transaction_type_enum', create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('real_estate_rentals',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('collected_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('pnu', sqlmodel.sql.sqltypes.AutoString(length=19), nullable=True),
    sa.Column('property_type', property_type_enum, nullable=False),
    sa.Column('transaction_type', transaction_type_enum, nullable=False),
    sa.Column('sigungu', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
    sa.Column('lot_number', sqlmodel.sql.sqltypes.AutoString(length=30), nullable=True),
    sa.Column('main_lot_number', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True),
    sa.Column('sub_lot_number', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True),
    sa.Column('road_name', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True),
    sa.Column('building_name', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True),
    sa.Column('exclusive_area', sa.Float(), nullable=True),
    sa.Column('land_area', sa.Float(), nullable=True),
    sa.Column('floor_area', sa.Float(), nullable=True),
    sa.Column('floor', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True),
    sa.Column('dong', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
    sa.Column('build_year', sa.Integer(), nullable=True),
    sa.Column('housing_type', sqlmodel.sql.sqltypes.AutoString(length=30), nullable=True),
    sa.Column('transaction_date', sa.Date(), nullable=True),
    sa.Column('rent_type', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True),
    sa.Column('deposit', sa.Integer(), nullable=True),
    sa.Column('monthly_rent_amount', sa.Integer(), nullable=True),
    sa.Column('contract_period', sqlmodel.sql.sqltypes.AutoString(length=30), nullable=True),
    sa.Column('contract_type', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True),
    sa.Column('renewal_right_used', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True),
    sa.Column('previous_deposit', sa.Integer(), nullable=True),
    sa.Column('previous_monthly_rent', sa.Integer(), nullable=True),
    sa.Column('deal_type', sqlmodel.sql.sqltypes.AutoString(length=30), nullable=True),
    sa.Column('broker_location', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_real_estate_rentals_building_name'), 'real_estate_rentals', ['building_name'], unique=False)
    op.create_index(op.f('ix_real_estate_rentals_pnu'), 'real_estate_rentals', ['pnu'], unique=False)
    op.create_index(op.f('ix_real_estate_rentals_sigungu'), 'real_estate_rentals', ['sigungu'], unique=False)
    op.create_index(op.f('ix_real_estate_rentals_transaction_date'), 'real_estate_rentals', ['transaction_date'], unique=False)
    op.create_table('real_estate_sales',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('collected_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('pnu', sqlmodel.sql.sqltypes.AutoString(length=19), nullable=True),
    sa.Column('property_type', property_type_enum, nullable=False),
    sa.Column('sigungu', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
    sa.Column('lot_number', sqlmodel.sql.sqltypes.AutoString(length=30), nullable=True),
    sa.Column('main_lot_number', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True),
    sa.Column('sub_lot_number', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True),
    sa.Column('road_name', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True),
    sa.Column('building_name', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True),
    sa.Column('exclusive_area', sa.Float(), nullable=True),
    sa.Column('land_area', sa.Float(), nullable=True),
    sa.Column('floor_area', sa.Float(), nullable=True),
    sa.Column('contract_area', sa.Float(), nullable=True),
    sa.Column('floor', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True),
    sa.Column('dong', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
    sa.Column('build_year', sa.Integer(), nullable=True),
    sa.Column('housing_type', sqlmodel.sql.sqltypes.AutoString(length=30), nullable=True),
    sa.Column('transaction_date', sa.Date(), nullable=True),
    sa.Column('transaction_amount', sa.Integer(), nullable=True),
    sa.Column('buyer_type', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('seller_type', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('deal_type', sqlmodel.sql.sqltypes.AutoString(length=30), nullable=True),
    sa.Column('broker_location', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
    sa.Column('registration_date', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('cancellation_date', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('land_category', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('use_area', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
    sa.Column('road_condition', sqlmodel.sql.sqltypes.AutoString(length=30), nullable=True),
    sa.Column('share_type', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_real_estate_sales_building_name'), 'real_estate_sales', ['building_name'], unique=False)
    op.create_index(op.f('ix_real_estate_sales_pnu'), 'real_estate_sales', ['pnu'], unique=False)
    op.create_index(op.f('ix_real_estate_sales_sigungu'), 'real_estate_sales', ['sigungu'], unique=False)
    op.create_index(op.f('ix_real_estate_sales_transaction_date'), 'real_estate_sales', ['transaction_date'], unique=False)
    op.drop_index(op.f('ix_real_estate_transactions_building_name'), table_name='real_estate_transactions')
    op.drop_index(op.f('ix_real_estate_transactions_pnu'), table_name='real_estate_transactions')
    op.drop_index(op.f('ix_real_estate_transactions_sigungu'), table_name='real_estate_transactions')
    op.drop_index(op.f('ix_real_estate_transactions_transaction_date'), table_name='real_estate_transactions')
    op.drop_table('real_estate_transactions')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table('real_estate_transactions',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
    sa.Column('collected_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('pnu', sa.VARCHAR(length=19), autoincrement=False, nullable=True),
    sa.Column('property_type', property_type_enum, autoincrement=False, nullable=False),
    sa.Column('transaction_type', transaction_type_enum, autoincrement=False, nullable=False),
    sa.Column('transaction_date', sa.DATE(), autoincrement=False, nullable=True),
    sa.Column('transaction_amount', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('sigungu', sa.VARCHAR(length=100), autoincrement=False, nullable=True),
    sa.Column('lot_number', sa.VARCHAR(length=30), autoincrement=False, nullable=True),
    sa.Column('main_lot_number', sa.VARCHAR(length=10), autoincrement=False, nullable=True),
    sa.Column('sub_lot_number', sa.VARCHAR(length=10), autoincrement=False, nullable=True),
    sa.Column('road_name', sa.VARCHAR(length=200), autoincrement=False, nullable=True),
    sa.Column('building_name', sa.VARCHAR(length=200), autoincrement=False, nullable=True),
    sa.Column('exclusive_area', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('land_area', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('floor_area', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('contract_area', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('floor', sa.VARCHAR(length=10), autoincrement=False, nullable=True),
    sa.Column('dong', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
    sa.Column('build_year', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('housing_type', sa.VARCHAR(length=30), autoincrement=False, nullable=True),
    sa.Column('buyer_type', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('seller_type', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('deal_type', sa.VARCHAR(length=30), autoincrement=False, nullable=True),
    sa.Column('broker_location', sa.VARCHAR(length=100), autoincrement=False, nullable=True),
    sa.Column('registration_date', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('cancellation_date', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('rent_type', sa.VARCHAR(length=10), autoincrement=False, nullable=True),
    sa.Column('deposit', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('monthly_rent_amount', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('contract_period', sa.VARCHAR(length=30), autoincrement=False, nullable=True),
    sa.Column('contract_type', sa.VARCHAR(length=10), autoincrement=False, nullable=True),
    sa.Column('renewal_right_used', sa.VARCHAR(length=10), autoincrement=False, nullable=True),
    sa.Column('previous_deposit', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('previous_monthly_rent', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('land_category', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('use_area', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
    sa.Column('road_condition', sa.VARCHAR(length=30), autoincrement=False, nullable=True),
    sa.Column('share_type', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('real_estate_transactions_pkey'))
    )
    op.create_index(op.f('ix_real_estate_transactions_transaction_date'), 'real_estate_transactions', ['transaction_date'], unique=False)
    op.create_index(op.f('ix_real_estate_transactions_sigungu'), 'real_estate_transactions', ['sigungu'], unique=False)
    op.create_index(op.f('ix_real_estate_transactions_pnu'), 'real_estate_transactions', ['pnu'], unique=False)
    op.create_index(op.f('ix_real_estate_transactions_building_name'), 'real_estate_transactions', ['building_name'], unique=False)
    op.drop_index(op.f('ix_real_estate_sales_transaction_date'), table_name='real_estate_sales')
    op.drop_index(op.f('ix_real_estate_sales_sigungu'), table_name='real_estate_sales')
    op.drop_index(op.f('ix_real_estate_sales_pnu'), table_name='real_estate_sales')
    op.drop_index(op.f('ix_real_estate_sales_building_name'), table_name='real_estate_sales')
    op.drop_table('real_estate_sales')
    op.drop_index(op.f('ix_real_estate_rentals_transaction_date'), table_name='real_estate_rentals')
    op.drop_index(op.f('ix_real_estate_rentals_sigungu'), table_name='real_estate_rentals')
    op.drop_index(op.f('ix_real_estate_rentals_pnu'), table_name='real_estate_rentals')
    op.drop_index(op.f('ix_real_estate_rentals_building_name'), table_name='real_estate_rentals')
    op.drop_table('real_estate_rentals')
