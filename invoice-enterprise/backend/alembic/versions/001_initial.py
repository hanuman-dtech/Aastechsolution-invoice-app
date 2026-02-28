"""Initial database schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-02-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='viewer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id', name='pk_users'),
        sa.UniqueConstraint('email', name='uq_users_email'),
    )
    op.create_index('ix_users_email_active', 'users', ['email', 'is_active'])

    # Vendors table
    op.create_table(
        'vendors',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('address_line1', sa.String(255), nullable=False),
        sa.Column('address_line2', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('province', sa.String(100), nullable=False),
        sa.Column('postal_code', sa.String(20), nullable=False),
        sa.Column('country', sa.String(100), nullable=False, server_default='Canada'),
        sa.Column('hst_number', sa.String(50), nullable=False),
        sa.Column('default_contractor', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id', name='pk_vendors'),
    )

    # Customers table
    op.create_table(
        'customers',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('address_line1', sa.String(255), nullable=False),
        sa.Column('address_line2', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('province', sa.String(100), nullable=False),
        sa.Column('postal_code', sa.String(20), nullable=False),
        sa.Column('country', sa.String(100), nullable=False, server_default='Canada'),
        sa.Column('contractor_name', sa.String(255), nullable=False),
        sa.Column('service_location', sa.String(255), nullable=False, server_default='Ontario, Canada'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], name='fk_customers_vendor_id_vendors', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_customers'),
    )
    op.create_index('ix_customers_vendor_active', 'customers', ['vendor_id', 'is_active'])
    op.create_index('ix_customers_name', 'customers', ['name'])

    # Contracts table
    op.create_table(
        'contracts',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('invoice_prefix', sa.String(10), nullable=False),
        sa.Column('frequency', sa.String(20), nullable=False, server_default='monthly'),
        sa.Column('default_hours', sa.Numeric(10, 2), nullable=False, server_default='40.00'),
        sa.Column('rate_per_hour', sa.Numeric(10, 2), nullable=False),
        sa.Column('hst_rate', sa.Numeric(5, 4), nullable=False, server_default='0.1300'),
        sa.Column('payment_terms', sa.String(50), nullable=False, server_default='Monthly'),
        sa.Column('extra_fees', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('extra_fees_label', sa.String(100), nullable=False, server_default='Other Fees'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name='fk_contracts_customer_id_customers', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_contracts'),
        sa.UniqueConstraint('customer_id', name='uq_contracts_customer_id'),
    )

    # Schedule configs table
    op.create_table(
        'schedule_configs',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('auto_send_email', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('timezone', sa.String(50), nullable=False, server_default='America/Toronto'),
        sa.Column('billing_weekday', sa.Integer(), nullable=False, server_default='4'),
        sa.Column('anchor_date', sa.Date(), nullable=False, server_default='2026-01-02'),
        sa.Column('billing_day', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('last_run_date', sa.Date(), nullable=True),
        sa.Column('next_run_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name='fk_schedule_configs_customer_id_customers', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_schedule_configs'),
        sa.UniqueConstraint('customer_id', name='uq_schedule_configs_customer_id'),
    )

    # Invoices table
    op.create_table(
        'invoices',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('invoice_number', sa.String(50), nullable=False),
        sa.Column('invoice_date', sa.Date(), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='generated'),
        sa.Column('total_hours', sa.Numeric(10, 2), nullable=False),
        sa.Column('rate_per_hour', sa.Numeric(10, 2), nullable=False),
        sa.Column('labor_subtotal', sa.Numeric(12, 2), nullable=False),
        sa.Column('extra_fees', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('extra_fees_label', sa.String(100), nullable=False, server_default='Other Fees'),
        sa.Column('subtotal', sa.Numeric(12, 2), nullable=False),
        sa.Column('hst_rate', sa.Numeric(5, 4), nullable=False),
        sa.Column('hst_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('total', sa.Numeric(12, 2), nullable=False),
        sa.Column('pdf_path', sa.String(500), nullable=True),
        sa.Column('generation_mode', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name='fk_invoices_customer_id_customers', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_invoices'),
        sa.UniqueConstraint('invoice_number', name='uq_invoices_invoice_number'),
    )
    op.create_index('ix_invoices_customer_date', 'invoices', ['customer_id', 'invoice_date'])
    op.create_index('ix_invoices_status', 'invoices', ['status'])
    op.create_index('ix_invoices_number', 'invoices', ['invoice_number'])

    # Invoice lines table
    op.create_table(
        'invoice_lines',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('quantity', sa.Numeric(10, 2), nullable=False),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('line_total', sa.Numeric(12, 2), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], name='fk_invoice_lines_invoice_id_invoices', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_invoice_lines'),
    )

    # Email logs table
    op.create_table(
        'email_logs',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('recipient_email', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(500), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], name='fk_email_logs_invoice_id_invoices', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_email_logs'),
    )
    op.create_index('ix_email_logs_status', 'email_logs', ['status'])
    op.create_index('ix_email_logs_invoice', 'email_logs', ['invoice_id'])

    # Execution logs table
    op.create_table(
        'execution_logs',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('run_date', sa.Date(), nullable=False),
        sa.Column('mode', sa.String(20), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('customers_loaded', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('schedule_matches', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pdfs_generated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('emails_sent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failures', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_trace', sa.Text(), nullable=True),
        sa.Column('request_id', sa.String(64), nullable=True),
        sa.Column('triggered_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id', name='pk_execution_logs'),
    )
    op.create_index('ix_execution_logs_run_date', 'execution_logs', ['run_date'])
    op.create_index('ix_execution_logs_mode', 'execution_logs', ['mode'])

    # SMTP configs table
    op.create_table(
        'smtp_configs',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('host', sa.String(255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False, server_default='587'),
        sa.Column('username', sa.String(255), nullable=False),
        sa.Column('encrypted_password', sa.String(500), nullable=False),
        sa.Column('from_email', sa.String(255), nullable=False),
        sa.Column('from_name', sa.String(255), nullable=True),
        sa.Column('use_tls', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], name='fk_smtp_configs_vendor_id_vendors', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_smtp_configs'),
    )
    op.create_index('ix_smtp_configs_vendor', 'smtp_configs', ['vendor_id'])


def downgrade() -> None:
    op.drop_table('smtp_configs')
    op.drop_table('execution_logs')
    op.drop_table('email_logs')
    op.drop_table('invoice_lines')
    op.drop_table('invoices')
    op.drop_table('schedule_configs')
    op.drop_table('contracts')
    op.drop_table('customers')
    op.drop_table('vendors')
    op.drop_table('users')
