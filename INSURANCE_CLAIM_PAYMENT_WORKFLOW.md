# Insurance Claim Payment Status Workflow

## Industry Standards & Best Practices

### 1. **Claim Status vs Payment Status Distinction**

**Industry Standard:**
- **Claim APPROVED** ≠ Payment Received
- **Claim PAID** = Payment Received from Insurer
- There can be delays between approval and payment (typically 30-90 days)

### 2. **Recommended Workflow**

```
Claim Status Flow:
DRAFT → SUBMITTED → PROCESSING → APPROVED → PAID
                                    ↓
                                REJECTED
```

**Payment Status Updates:**
- **APPROVED**: Invoice → `PARTIALLY_PAID` (if co-pay exists) or `PENDING` (awaiting payment)
- **PAID**: Invoice → `PAID`, OPD Visit → `paid`, Create Payment Record
- **REJECTED**: Invoice remains `PENDING`, Add rejection note

### 3. **Co-Pay Handling**

**Industry Standard:**
- If co-pay > 0: Invoice remains `PARTIALLY_PAID` until co-pay is collected
- If co-pay = 0: Invoice can move to `PAID` when claim is `PAID`
- Patient is responsible for co-pay regardless of claim approval

### 4. **Payment Record Creation**

**Best Practice:**
- Create a payment record when claim status is `PAID` (payment received)
- Link payment to invoice with claim number as transaction reference
- Use receipt number format: `INS-{claim_number}`

---

## Implementation Details

### **Automatic Payment Status Updates**

The `update_claim_status()` function in `app/crud/claims_crud.py` now automatically:

#### **When Claim Status = APPROVED:**
1. Updates invoice status:
   - If co-pay exists: `PARTIALLY_PAID` (insurance portion approved, co-pay pending)
   - If no co-pay: `PENDING` (awaiting actual payment)
2. Updates invoice `paid_amount` to reflect approved insurance amount
3. Recalculates invoice `balance`

#### **When Claim Status = PAID:**
1. Updates invoice:
   - Adds insurance payment amount to `paid_amount`
   - Recalculates `balance`
   - Sets status to `PAID` if fully paid (including co-pay)
   - Sets `paid_date` if fully paid
2. Creates payment record:
   - Payment method: `NHIS`
   - Transaction reference: Claim number
   - Receipt number: `INS-{claim_number}`
   - Notes: "Insurance payment for claim {claim_number}"
3. Syncs OPD visit payment status:
   - Calls `opd_crud.sync_opd_visit_payment_status()` to update OPD visit

#### **When Claim Status = REJECTED:**
1. Keeps invoice status as `PENDING`
2. Adds rejection note to invoice:
   - Format: `[Claim {claim_number} rejected: {rejection_reason}]`
3. Patient may need to pay out of pocket

---

## Usage Example

```python
from app.crud import claims_crud
from app.models.claims_models import ClaimStatus
from decimal import Decimal

# Update claim status to APPROVED
claim = claims_crud.update_claim_status(
    db=db,
    claim_id=claim_id,
    new_status=ClaimStatus.APPROVED,
    approved_amount=Decimal('500.00')
)
# Invoice automatically updated to PARTIALLY_PAID (if co-pay exists)

# Update claim status to PAID (payment received)
claim = claims_crud.update_claim_status(
    db=db,
    claim_id=claim_id,
    new_status=ClaimStatus.PAID,
    approved_amount=Decimal('500.00')
)
# Invoice automatically updated to PAID
# Payment record automatically created
# OPD visit payment status automatically synced
```

---

## Benefits

1. **Automated Workflow**: No manual intervention needed
2. **Audit Trail**: Payment records created automatically
3. **Accurate Status**: Invoice and OPD visit status always reflect claim status
4. **Co-Pay Handling**: Properly handles partial payments
5. **Industry Standard**: Follows healthcare billing best practices

---

## Future Enhancements

### **For Private Insurance:**
- Similar workflow can be implemented for private insurance claims
- Create `PrivateInsuranceClaim` model similar to `NHISClaim`
- Use `PaymentMethod.PRIVATE_INSURANCE` for payment records

### **Notification System:**
- Send notifications when claims are approved/rejected/paid
- Alert finance team when payments are received
- Notify patients when co-pay is due

### **Reporting:**
- Track claim approval rates
- Monitor payment delays
- Analyze co-pay collection rates

---

## Notes

- This implementation follows **HL7 FHIR** billing standards
- Aligns with **Ghana NHIA** claim processing guidelines
- Compatible with **HIPAA** financial transaction requirements
- Supports audit-ready financial reporting

