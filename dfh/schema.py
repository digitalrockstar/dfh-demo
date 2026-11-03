"""Schema for all modules, defined as compact text and built into SQLAlchemy Core tables.
Column spec: name type [flags]. Types: i int, b bigint, f float, d date, dt datetime, bo bool, j json,
t text, sN string(N). Flags: N nullable, U unique, I index, P primary key (several P = composite),
fk=table.col. Tables without a P column get an auto integer id.
Money is bigint paise (or minor units of a stated currency). Quantities are integers in the SKU base
unit: grams for bulk (loose) SKUs, units for packed SKUs."""
import re
from sqlalchemy import (MetaData, Table, Column, Integer, BigInteger, String, Text, Float, Date,
                        DateTime, Boolean, JSON, ForeignKey, Index)

SCHEMA_TEXT = """
## platform
legal_entity: code s20 U; name s120; country s40; currency s3; state s40 N; gstin s24 N; is_demo bo
fx_rate: currency s3 I; month d; rate_to_inr f; assumed bo
role: code s20 U; name s60
app_user: username s40 U; name s80; role_id i fk=role.id; scope_type s12; scope_id i N; password_hash s200; active bo; last_login dt N; employee_id i N
audit_log: ts dt I; user_id i N; device_id i N; action s40; table_name s60; row_id s40; before j N; after j N
approval_rule: doc_type s30; min_amount_paise b; max_amount_paise b N; approver_role_id i fk=role.id
approval_request: doc_type s30; doc_id s40; requested_by i N; status s12; approver_id i N; amount_paise b; created_at dt; decided_at dt N; note t N
notification: user_id i I; channel s12; title s120; body t; ref_type s30 N; ref_id s40 N; created_at dt; read_at dt N
import_job: kind s30; filename s200; status s12; rows_ok i; rows_err i; created_at dt; report j N
device: store_id i fk=location.id I; code s30 U; kind s12; last_seen_at dt N; app_version s12; active bo
invoice_series: device_id i fk=device.id; fy s7; prefix s24; next_no i; reserved_to i
sync_log: device_id i fk=device.id I; started_at dt; finished_at dt N; bills_pushed i; bills_rejected i; queue_depth i; status s12
festival_calendar: name s60; start_date d; end_date d; peak_date d; ramp_days i; uplift f; regions s20; assumed bo
demo_finding: code s10 U; module s30; title s160; description t; params j
## masters
location: code s30 U; name s120; type s12 I; city s40 I; state s40; country s40; region s12; parent_id i N fk=location.id; entity_id i fk=legal_entity.id; serving_wh_id i N fk=location.id; format s20 N; tier s8 N; area_sqft i N; opened_on d N; is_port bo; last_sync_at dt N; active bo; lat f N; lng f N
location_bin: warehouse_id i fk=location.id I; zone s8; rack s8; bin_code s30 U
category: code s8 U; name s60; parent_id i N fk=category.id; site_collection bo
product: code s30 U; name s120; category_id i fk=category.id I; origins s60; hsn s10; shelf_life_days i; storage s30; is_fresh bo; popularity f
sku: code s40 U; barcode s20 U; product_id i fk=product.id I; name s160; grade s30 N; pack_g i N; base_uom s3; procurement_type s10 I; bulk_sku_id i N fk=sku.id; status s10; shelf_life_days i; hsn s10; mrp_paise b N; price_per_kg_paise b N; std_cost_paise b; popularity f
tax_rate: hsn s10 U; description s120; rate_loose_pct f; rate_packed_pct f; assumed bo
tax_assumption: assumption_key s40 U; value s200; note t
price_list: code s20 U; name s80; scope_type s12; scope_value s40
price_list_item: price_list_id i fk=price_list.id I; sku_id i fk=sku.id I; price_paise b; effective_from d; effective_to d N
kit_bom: kit_sku_id i fk=sku.id I; component_sku_id i fk=sku.id; qty i
store_assortment: store_id i P fk=location.id; sku_id i P fk=sku.id; min_qty b; max_qty b; listed_from d
## procurement
vendor: code s20 U; name s120; type s10; country s3; city s40; currency s3; categories s60; payment_terms_days i; gstin s24 N; active bo; is_trader bo
vendor_sku_cost: vendor_id i fk=vendor.id; sku_id i fk=sku.id; currency s3; price_minor b; price_per s2; incoterm s3; moq_qty b; lead_time_days i; effective_from d; effective_to d N
purchase_order: po_no s30 U; vendor_id i fk=vendor.id I; dest_location_id i fk=location.id; status s12 I; currency s3; fx_rate f; order_date d; expected_date d; approved_by i N; total_minor b; notes t N
purchase_order_line: po_id i fk=purchase_order.id I; sku_id i fk=sku.id; qty b; price_minor b
shipment: ship_no s30 U; po_id i fk=purchase_order.id I; mode s6; container_no s20 N; port_id i N fk=location.id; status s16 I; etd d N; eta d N; ata d N; bl_no s30 N
shipment_event: shipment_id i fk=shipment.id I; status s16; ts dt; note t N
landed_cost: shipment_id i fk=shipment.id I; component s16; amount_paise b; currency s3; fx_rate f
## inventory
batch: batch_no s40 U; sku_id i fk=sku.id I; vendor_id i N fk=vendor.id; received_on d; mfg_date d N; expiry_date d I; mrp_paise b N; unit_cost_paise b; source_doc_type s20; source_doc_id s40
grn: grn_no s30 U; po_id i N fk=purchase_order.id; shipment_id i N fk=shipment.id; location_id i fk=location.id; received_at dt; status s12; received_by i N
grn_line: grn_id i fk=grn.id I; sku_id i fk=sku.id; batch_id i N fk=batch.id; qty_received b; qty_accepted b; qty_rejected b; reject_reason s40 N; unit_cost_paise b
vendor_invoice: vendor_id i fk=vendor.id I; po_id i N fk=purchase_order.id; inv_no s40; inv_date d; amount_minor b; currency s3; status s12; due_date d; note t N; entity_id i N fk=legal_entity.id; taxable_minor b N; tax_minor b N
vendor_payment: vendor_id i fk=vendor.id I; invoice_id i N fk=vendor_invoice.id; paid_on d; amount_minor b; mode s12; fx_rate f
debit_note: vendor_id i fk=vendor.id; grn_id i N fk=grn.id; amount_paise b; reason s60; created_at dt
stock_ledger: ts dt; location_id i fk=location.id; bin_id i N fk=location_bin.id; sku_id i fk=sku.id; batch_id i N fk=batch.id; qty b; movement_type s20; doc_type s20; doc_id s40; unit_cost_paise b N; user_id i N; device_id i N
stock_balance: location_id i P fk=location.id; sku_id i P fk=sku.id; batch_id i P; qty b; updated_at dt
transfer: transfer_no s30 U; indent_id i N; from_location_id i fk=location.id; to_location_id i fk=location.id; status s12 I; created_at dt; dispatched_at dt N; received_at dt N; vehicle_no s20 N; eway_ref s30 N
transfer_line: transfer_id i fk=transfer.id I; sku_id i fk=sku.id; batch_id i N fk=batch.id; qty_sent b; qty_received b N
indent: indent_no s30 U; store_id i fk=location.id I; warehouse_id i fk=location.id; status s12; created_at dt; needed_by d
indent_line: indent_id i fk=indent.id I; sku_id i fk=sku.id; qty_req b; qty_alloc b; qty_dispatched b
pick: indent_line_id i fk=indent_line.id; batch_id i fk=batch.id; qty b; picked_at dt N
repack_job: job_no s30 U; warehouse_id i fk=location.id; bulk_sku_id i fk=sku.id; input_batch_id i fk=batch.id; input_g b; status s12; started_at dt; finished_at dt N; operator_id i N; loss_g b N
repack_output: job_id i fk=repack_job.id I; sku_id i fk=sku.id; batch_id i N fk=batch.id; units i
count_plan: plan_no s30 U; location_id i fk=location.id; abc_class s1; planned_on d; status s12
count_line: plan_id i fk=count_plan.id I; sku_id i fk=sku.id; batch_id i N fk=batch.id; system_qty b; counted_qty b N; variance_qty b N; approved_by i N
bulk_order: order_no s30 U; customer_id i N fk=customer.id; type s12; status s12; location_id i fk=location.id; created_at dt; due_date d; total_paise b
bulk_order_line: order_id i fk=bulk_order.id I; sku_id i fk=sku.id; qty b; price_paise b
## pos
sale: id s36 P; store_id i fk=location.id I; device_id i fk=device.id; invoice_no s40 U; business_date d I; created_at_device dt; received_at dt; cashier_id i N; customer_id i N fk=customer.id; gross_paise b; discount_paise b; tax_paise b; net_paise b; round_off_paise i; status s12; void_reason s60 N; price_list_id i N fk=price_list.id; idem_key s64 U; currency s3
sale_line: sale_id s36 fk=sale.id I; sku_id i fk=sku.id; batch_id i N fk=batch.id; qty b; unit_price_paise b; discount_paise b; tax_rate f; tax_paise b; net_paise b; hsn s10
payment: sale_id s36 fk=sale.id I; mode s10; amount_paise b; ref s60 N; status s10
sale_return: return_no s30 U; sale_id s36 fk=sale.id I; store_id i fk=location.id; created_at dt; reason s12; status s12; approved_by i N; refund_paise b; days_since_sale i
sale_return_line: return_id i fk=sale_return.id I; sale_line_id i fk=sale_line.id; qty b; disposition s16
day_close: store_id i fk=location.id I; business_date d; device_id i N fk=device.id; opened_by i N; closed_by i N; opening_cash_paise b; expected_cash_paise b; counted_cash_paise b N; variance_paise b N; status s10; closed_at dt N
cash_drop: day_close_id i fk=day_close.id; amount_paise b; ts dt; by_user i N
coupon: code s20 U; type s8; value f; valid_from d; valid_to d; active bo
## wastage
wastage_reason: code s16 U; name s60; is_controllable bo; cap_pct f N
wastage_entry: ts dt I; location_id i fk=location.id I; sku_id i fk=sku.id; batch_id i N fk=batch.id; qty b; reason s16; cost_paise b; entered_by i N; status s10; approved_by i N; photo_ref s120 N; vendor_claim bo
markdown_suggestion: location_id i fk=location.id; batch_id i fk=batch.id; suggested_pct f; reason s60; created_at dt; status s10
## finance
account: code s10 U; name s80; type s12
journal_entry: jv_no s30 U; date d I; entity_id i fk=legal_entity.id; source_doc_type s20; source_doc_id s40; narration s200
journal_line: jv_id i fk=journal_entry.id I; account_code s10; debit_paise b; credit_paise b; location_id i N fk=location.id
settlement: store_id i N fk=location.id; mode s10; settle_date d; business_date d I; expected_paise b; received_paise b; fee_paise b; ref s60 N; status s10
recon_item: source s20; source_ref s60; store_id i N fk=location.id; business_date d; amount_paise b; matched_to s60 N; status s12; note t N; resolved_by i N; resolved_at dt N
gst_return_period: entity_id i fk=legal_entity.id; period s7; status s10; locked_at dt N
gstr2b_line: entity_id i fk=legal_entity.id; period s7; supplier_gstin s24; inv_no s40; taxable_paise b; tax_paise b; matched_invoice_id i N fk=vendor_invoice.id; status s10
period_lock: entity_id i fk=legal_entity.id; period s7; locked_at dt; locked_by i N
## crm
customer: code s20 U; phone s20 U; name s80 N; city s40; created_at dt; first_store_id i N fk=location.id; consent_wa bo; consent_at dt N; loyalty_points i; segment s20 N
loyalty_txn: customer_id i fk=customer.id I; sale_id s36 N fk=sale.id; points i; ts dt; kind s10
wa_order: order_no s30 U; customer_id i fk=customer.id; status s12; source s12; created_at dt; total_paise b; payment_link s200 N
wa_order_line: order_id i fk=wa_order.id I; sku_id i fk=sku.id; qty b; price_paise b
quote: quote_no s30 U; company s120; contact s80; status s12; created_at dt; valid_to d; total_paise b
quote_line: quote_id i fk=quote.id I; sku_id i fk=sku.id; qty b; price_paise b
campaign: name s120; template s80; segment s40; scheduled_at dt; status s12; sent i; delivered i; replied i
## hr
department: name s60 U
designation: title s60 U; level i
employee: emp_code s20 U; name s80; department_id i fk=department.id; designation_id i fk=designation.id; location_id i fk=location.id I; manager_id i N fk=employee.id; join_date d; birth_date d; status s10; email s120 N
shift: code s10 U; start_time s5; end_time s5
attendance: employee_id i fk=employee.id; date d; punch_in dt N; punch_out dt N; source s10; location_id i fk=location.id; hours f N; status s10
roster: employee_id i fk=employee.id; date d; shift_id i fk=shift.id; location_id i fk=location.id
leave_type: code s10 U; name s40; annual_quota i
leave_request: employee_id i fk=employee.id I; leave_type_id i fk=leave_type.id; from_date d; to_date d; status s10; is_wfh bo; approver_id i N fk=employee.id
holiday: date d; name s80; state s40 N
onboarding_task: employee_id i fk=employee.id I; task s120; due_date d; done_at dt N
job_posting: title s120; department_id i fk=department.id; location_id i N fk=location.id; status s10; posted_on d; closes_on d N; description t
applicant: job_id i fk=job_posting.id I; name s80; stage s16; applied_on d; source s20
announcement: title s120; body t; created_at dt; audience s30
## analytics
forecast_run: run_at dt; method s30; horizon_weeks i; wape f N; notes t N
forecast: run_id i fk=forecast_run.id I; store_id i fk=location.id; sku_id i fk=sku.id I; week_start d; qty_forecast f; lower f; upper f; value_paise b
reorder_suggestion: run_id i N fk=forecast_run.id; location_id i fk=location.id I; sku_id i fk=sku.id I; vendor_id i N fk=vendor.id; suggested_qty b; approved_qty b N; unit_cost_paise f; value_paise b; on_hand b; on_order b; need_lead b; need_cycle b; cover_days f; lead_time_days i; moq b; urgency s8 I; order_by d; reason s200; status s10 I; created_at dt; decided_by i N; decided_at dt N; po_id i N fk=purchase_order.id
stock_position: location_id i P fk=location.id; sku_id i P fk=sku.id; on_hand b; on_order b; eta_days i; as_of d
demand_requirement: run_id i fk=forecast_run.id; location_id i fk=location.id I; sku_id i fk=sku.id I; need_qty b; base_qty b; kit_qty b; need_lead b
kpi_snapshot: date d I; kpi s40 I; dim_type s12; dim_id i N; value f
exception_item: ts dt I; type s30 I; severity s6; location_id i N fk=location.id; ref_type s30 N; ref_id s40 N; title s160; status s10; owner_id i N; due_date d N
"""

IDX = {
    "stock_ledger": [["location_id", "sku_id", "ts"], ["batch_id"], ["movement_type", "ts"]],
    "transfer": [["from_location_id"], ["to_location_id"], ["indent_id"]],
    "vendor_sku_cost": [["vendor_id", "sku_id", "effective_from"], ["sku_id"]],
    "sale": [["store_id", "business_date"]],
    "attendance": [["employee_id", "date"]],
    "wastage_entry": [["location_id", "ts"]],
    "forecast": [["store_id", "sku_id", "week_start"]],
    "price_list_item": [["price_list_id", "sku_id"]],
    "settlement": [["store_id", "settle_date"]],
    "day_close": [["store_id", "business_date"]],
    "recon_item": [["status", "source"]],
    "journal_entry": [["entity_id", "date"]],
    "vendor_invoice": [["entity_id", "inv_date"]],
}
TYPES = {"i": Integer, "b": BigInteger, "t": Text, "f": Float, "d": Date, "dt": DateTime,
         "bo": Boolean, "j": JSON}


def _type(tok):
    return String(int(tok[1:])) if re.fullmatch(r"s\d+", tok) else TYPES[tok]()


def build_metadata():
    md, module_of, mod = MetaData(), {}, None
    for raw in SCHEMA_TEXT.strip().splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("## "):
            mod = line[3:]
            continue
        name, spec = line.split(":", 1)
        cols, has_pk = [], False
        for c in spec.split(";"):
            p = c.split()
            kw, args = {"nullable": False}, []
            for f in p[2:]:
                if f == "N": kw["nullable"] = True
                elif f == "U": kw["unique"] = True
                elif f == "I": kw["index"] = True
                elif f == "P": kw["primary_key"] = True; has_pk = True
                elif f.startswith("fk="): args.append(ForeignKey(f[3:]))
            if p[1] == "bo": kw["default"] = False
            cols.append(Column(p[0], _type(p[1]), *args, **kw))
        if not has_pk:
            cols.insert(0, Column("id", Integer, primary_key=True, autoincrement=True))
        Table(name.strip(), md, *cols)
        module_of[name.strip()] = mod
    for t, idxs in IDX.items():
        for cols in idxs:
            Index(f"ix_{t}_{'_'.join(cols)}", *[md.tables[t].c[c] for c in cols])
    return md, module_of


metadata, MODULE_OF = build_metadata()
