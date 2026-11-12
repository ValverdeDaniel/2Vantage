"""The four carrier census formats (plan.md §9.8; K36, K88, K93, K95, K96; OQ109). A data module, exempt from the
300-line rule; never retyped.

Generated on 2026-11-12 from old Vantage at commit 891f1b3:
- the `CarrierTemplate` rows of a migrated old database (the parity app's, migrated through 0054, 0055, 0061, 0065 and
  0066, dumped read-only): geometry, columns, the group-information cells, caps, formats and versions;
- `benefits/reports/census_mapping.py` `GAP_HOMES` and `UNWRITTEN_COLUMNS` (what each gap means, judgment);
- the bundled workbooks in `assets/carrier_templates/` (byte for byte, hash-checked): `not_sent`, the carrier's columns
  past the ones we write, with whether their first data cell is a formula (UHC's enrollment half, Y–BX).
Diffed column by column against `PlanningDocs/Benefits/carrier-census-templates_20260917.md`: no difference. The live
rows of the real old app were not read (that database is never touched); its admin could have edited them.

Renamed keys: `canonical_field` → `field`, `dependent_inherits` → `inherits`, `template_file` → `file`, `origin_col` →
`origin`, `clear_ranges` → `clear`. Dropped (K38, K94, K95): `row_scope` (every live format is one row per member),
`size_band`, `tier_codes`, `active`, admin editing and the fresh-workbook path.

A column: `{header, hint, field | source, transform, value_map, required, employee_only, line, inherits}`. Sources:
`row:member_type`, `row:enroll:<census key>`, `derive:age | county | out_of_area`. Transforms: `tier`, `gender`,
`status`, `date`, `zip5`, `initial`. A carrier asterisk on a header (`*Gender`, `Zip*`) also makes a column required
(`translate.column_required`).

OQ109, checked against `warner_census.xlsx` on 2026-11-12: S3 reads "CLASSES " under the merged BASIC LIFE banner
(R2:S2) and X3 "CLASSES" under the DISABILITY banner (U2:X2); both hints read "If multiple classes please list". They
are the life and the disability class of one employee, and our census holds one class per employee, so `emp_class`
fills both, ungated by line, as the old final state does.
"""

# Keyed by the old template key (`rfp.carriers.ATTRIBUTES[*]['census_format']`); `file_key` names the format in the one
# key space (`census-<file_key>`, K.6); `carrier_key` is the carrier in `deals/carriers.py` ('' for Warner's universal).
DEFINITIONS = {
    'warner_census': {
        'key': 'warner_census',
        'file_key': 'warner',
        'carrier': 'Warner Pacific',
        'carrier_key': '',
        'label': 'Warner Pacific census',
        'file': 'warner_census.xlsx',
        'sheet': 'Census Template',
        'header_row': 3,
        'data_row': 7,
        'origin': 'B',
        'clear': ['A5:X6'],
        'max_rows': 500,
        'formats': ['xlsx'],
        'version': 'rev8.20.26 (from the SG quote request form)',
        'columns': [
            {
                'header': 'RELATIONSHIP',
                'source': 'row:member_type',
                'value_map': {
                    'child': 'Child/Dependent',
                    'spouse': 'Spouse/Partner',
                    'employee': 'Employee',
                    'domestic_partner': 'Spouse/Partner',
                },
                'required': True,
            },
            {'header': 'MEMBER NAME', 'hint': 'First', 'field': 'first_name', 'required': True},
            {'hint': 'Last', 'field': 'last_name', 'required': True},
            {'header': 'DATE OF BIRTH', 'field': 'dob', 'transform': 'date', 'required': True},
            {
                'header': 'GENDER',
                'field': 'gender',
                'transform': 'gender',
                'value_map': {'F': 'F', 'M': 'M'},
                'required': True,
            },
            {'header': 'ZIP CODE', 'field': 'zip', 'transform': 'zip5', 'required': True, 'inherits': True},
            {'header': 'COUNTY', 'source': 'derive:county'},
            {'header': 'HOURS', 'hint': 'Per week', 'field': 'hours_per_week'},
            {
                'header': 'EE STATUS',
                'field': 'employment_status',
                'transform': 'status',
                'value_map': {'COBRA': 'COBRA', 'ACTIVE': 'Active'},
                'employee_only': True,
            },
            {
                'header': 'COVERAGE TYPE',
                'field': 'medical_tier',
                'transform': 'tier',
                'value_map': {'EC': 'EC', 'EE': 'EE', 'ES': 'ES', 'FAM': 'EF', 'WAIVE': 'Waive'},
                'required': True,
                'employee_only': True,
                'line': 'medical',
            },
            {'header': 'WAIVE REASON', 'field': 'waiver_reason'},
            {'header': 'CURRENT PLAN ELECTION', 'field': 'medical_plan', 'employee_only': True, 'line': 'medical'},
            {
                'header': 'COVERAGE TYPE',
                'field': 'dental_tier',
                'transform': 'tier',
                'value_map': {'EC': 'EC', 'EE': 'EE', 'ES': 'ES', 'FAM': 'EF', 'WAIVE': 'Waive'},
                'employee_only': True,
                'line': 'dental',
            },
            {'header': 'CURRENT PLAN ELECTION', 'field': 'dental_plan', 'employee_only': True, 'line': 'dental'},
            {
                'header': 'COVERAGE TYPE',
                'field': 'vision_tier',
                'transform': 'tier',
                'value_map': {'EC': 'EC', 'EE': 'EE', 'ES': 'ES', 'FAM': 'EF', 'WAIVE': 'Waive'},
                'employee_only': True,
                'line': 'vision',
            },
            {'header': 'CURRENT PLAN ELECTION', 'field': 'vision_plan', 'employee_only': True, 'line': 'vision'},
            {
                'header': 'COVERAGE TYPE',
                'source': 'row:enroll:basic_life_amount',
                'value_map': {'ENROLL': 'Enroll'},
                'employee_only': True,
                'line': 'basic_life_add',
            },
            {'header': 'CLASSES', 'field': 'emp_class', 'employee_only': True},
            {'header': 'ELECTIONS', 'field': 'vol_life_amount', 'employee_only': True, 'line': 'voluntary_life'},
            {'header': 'SALARY', 'field': 'annual_salary', 'employee_only': True},
            {
                'header': 'PAY MODE',
                'source': 'row:enroll:annual_salary',
                'value_map': {'ENROLL': 'Annual'},
                'employee_only': True,
            },
            {'header': 'JOB TITLE', 'field': 'job_title', 'employee_only': True},
            {'header': 'CLASSES', 'field': 'emp_class', 'employee_only': True},
        ],
        'group_info': [],
        'gaps': [],
        'not_sent': {},
    },
    'aetna_gateway': {
        'key': 'aetna_gateway',
        'file_key': 'aetna',
        'carrier': 'Aetna',
        'carrier_key': 'aetna',
        'label': 'Aetna Gateway census',
        'file': 'aetna_gateway_census.xlsx',
        'sheet': 'Census Input',
        'header_row': 6,
        'data_row': 7,
        'origin': 'A',
        'clear': ['A4:I4'],
        'max_rows': 485,
        'formats': ['xlsx'],
        'version': 'AFA Census Template (2025-07-15)',
        'columns': [
            {'header': 'Last Name', 'field': 'last_name', 'required': True},
            {'header': 'First Name', 'field': 'first_name', 'required': True},
            {'header': 'Home Zip Code', 'field': 'zip', 'transform': 'zip5', 'required': True, 'inherits': True},
            {'header': 'Date of Birth', 'field': 'dob', 'transform': 'date', 'required': True},
            {
                'header': 'Gender',
                'field': 'gender',
                'transform': 'gender',
                'value_map': {'F': 'F', 'M': 'M'},
                'required': True,
            },
            {
                'header': 'Medical Tier',
                'field': 'medical_tier',
                'transform': 'tier',
                'value_map': {'EC': 'EEChren', 'EE': 'EEOnly', 'ES': 'EESpOnly', 'FAM': 'EEFamily', 'WAIVE': 'Waive'},
                'required': True,
                'employee_only': True,
                'line': 'medical',
            },
            {
                'header': 'Dental Tier',
                'field': 'dental_tier',
                'transform': 'tier',
                'value_map': {'EC': 'EEChren', 'EE': 'EEOnly', 'ES': 'EESpOnly', 'FAM': 'EEFamily', 'WAIVE': 'Waive'},
                'employee_only': True,
                'line': 'dental',
            },
            {
                'header': 'Member Type',
                'source': 'row:member_type',
                'value_map': {'child': 'CH', 'spouse': 'SP', 'employee': 'EE', 'domestic_partner': 'SP'},
                'required': True,
            },
            {
                'header': 'Subscriber Employment Status',
                'field': 'employment_status',
                'transform': 'status',
                'value_map': {'COBRA': 'Cobra', 'STCON': 'St Con', 'ACTIVE': 'Active', 'RETIREE': 'Retiree'},
                'employee_only': True,
            },
        ],
        'group_info': [{'cell': 'J1', 'sheet': 'Census Input', 'source': 'rfp.aetna_underwriting'}],
        'gaps': [],
        'not_sent': {},
    },
    'angle': {
        'key': 'angle',
        'file_key': 'angle',
        'carrier': 'Angle Health',
        'carrier_key': 'angle_health',
        'label': 'Angle Health census',
        'file': 'angle_census.xlsx',
        'sheet': 'Sheet1',
        'header_row': 9,
        'data_row': 10,
        'origin': 'B',
        'clear': ['B10:I10'],
        'max_rows': 213,
        'formats': ['xlsx', 'csv'],
        'version': '2023-10-11',
        'columns': [
            {'header': 'First Name*', 'field': 'first_name', 'required': True},
            {'header': 'Last Name*', 'field': 'last_name', 'required': True},
            {
                'header': 'Relationship* (Employee/Spouse/Child)',
                'source': 'row:member_type',
                'value_map': {
                    'child': 'Child',
                    'spouse': 'Spouse',
                    'employee': 'Employee',
                    'domestic_partner': 'Spouse',
                },
                'required': True,
            },
            {
                'header': 'Gender* (Female/Male)',
                'field': 'gender',
                'transform': 'gender',
                'value_map': {'F': 'Female', 'M': 'Male'},
                'required': True,
            },
            {'header': 'Date of Birth* (MM/DD/YYYY)', 'field': 'dob', 'transform': 'date', 'required': True},
            {'header': 'Zip*', 'field': 'zip', 'transform': 'zip5', 'required': True, 'inherits': True},
            {
                'header': 'Tier*',
                'field': 'medical_tier',
                'transform': 'tier',
                'value_map': {
                    'EC': 'Employee+Child(ren)',
                    'EE': 'Employee',
                    'ES': 'Employee+Spouse',
                    'FAM': 'Employee+Family',
                },
                'required': True,
                'employee_only': True,
                'line': 'medical',
            },
            {'header': 'Plan Name', 'field': 'medical_plan', 'employee_only': True, 'line': 'medical'},
        ],
        'group_info': [],
        'gaps': [],
        'not_sent': {},
    },
    'uhc': {
        'key': 'uhc',
        'file_key': 'uhc',
        'carrier': 'UnitedHealthcare',
        'carrier_key': 'unitedhealthcare',
        'label': 'UnitedHealthcare census',
        'file': 'uhc_census.xlsx',
        'sheet': 'Employee Info',
        'header_row': 3,
        'data_row': 4,
        'origin': 'A',
        'clear': [],
        'max_rows': 350,
        'formats': ['xlsx'],
        'version': 'V1.012025',
        'columns': [
            {
                'header': '*Type',
                'source': 'row:member_type',
                'value_map': {
                    'child': 'Dependent',
                    'spouse': 'Dependent',
                    'employee': 'Employee',
                    'domestic_partner': 'Dependent',
                },
                'required': True,
            },
            {
                'header': 'Relationship (Required if dependent)',
                'source': 'row:member_type',
                'value_map': {
                    'child': 'Child',
                    'spouse': 'Spouse',
                    'employee': '',
                    'domestic_partner': 'Domestic Partner',
                },
            },
            {'header': 'Applicant Id'},
            {'header': 'Individual Applicant Id'},
            {'header': 'Zip Code (Required if Level Funded)', 'field': 'zip', 'transform': 'zip5', 'inherits': True},
            {'header': 'Last Name (Required if Level Funded)', 'field': 'last_name', 'required': True},
            {'header': 'First Name (Required if Level Funded)', 'field': 'first_name', 'required': True},
            {'header': 'Middle Initial (optional)', 'field': 'middle_name', 'transform': 'initial'},
            {
                'header': '*Date of Birth (Required if Level Funded) (MM/DD/YYYY)',
                'field': 'dob',
                'transform': 'date',
                'required': True,
            },
            {'header': 'Age (Age or DOB required if Fully Insured)', 'source': 'derive:age'},
            {
                'header': '*Gender',
                'field': 'gender',
                'transform': 'gender',
                'value_map': {'F': 'Female', 'M': 'Male'},
                'required': True,
            },
            {
                'header': '*Employee Status',
                'field': 'employment_status',
                'transform': 'status',
                'value_map': {'COBRA': 'Cobra', 'ACTIVE': 'Active'},
                'employee_only': True,
            },
            {'header': 'Employee Class', 'field': 'emp_class', 'employee_only': True},
            {'header': 'Special Employee'},
            {'header': 'Email', 'field': 'email'},
            {'header': 'Salary', 'field': 'annual_salary', 'employee_only': True},
            {'header': '*Out of Area (Medical Only)', 'source': 'derive:out_of_area', 'value_map': {'IN_AREA': 'No'}},
            {
                'header': 'Medical Coverage Type (Required if quoting product)',
                'field': 'medical_tier',
                'transform': 'tier',
                'value_map': {
                    'EC': 'Employee & Child',
                    'EE': 'Employee Only',
                    'ES': 'Employee & Spouse',
                    'FAM': 'Employee & Family',
                    'WAIVE': 'Waive',
                },
                'required': True,
                'employee_only': True,
                'line': 'medical',
            },
            {'header': 'Medical Waiver Reason', 'field': 'waiver_reason'},
            {
                'header': 'Dental Coverage Type (Required if quoting product)',
                'field': 'dental_tier',
                'transform': 'tier',
                'value_map': {
                    'EC': 'Employee & Child',
                    'EE': 'Employee Only',
                    'ES': 'Employee & Spouse',
                    'FAM': 'Employee & Family',
                    'WAIVE': 'Waive',
                },
                'employee_only': True,
                'line': 'dental',
            },
            {
                'header': 'Vision Coverage Type (Required if quoting product)',
                'field': 'vision_tier',
                'transform': 'tier',
                'value_map': {
                    'EC': 'Employee & Child',
                    'EE': 'Employee Only',
                    'ES': 'Employee & Spouse',
                    'FAM': 'Employee & Family',
                    'WAIVE': 'Waive',
                },
                'employee_only': True,
                'line': 'vision',
            },
            {
                'header': 'Life Coverage Type (Required if quoting product)',
                'source': 'row:enroll:basic_life_amount',
                'value_map': {'ENROLL': 'Employee Only'},
                'employee_only': True,
                'line': 'basic_life_add',
            },
            {
                'header': 'Short Term Disability Coverage Type (Required if quoting product)',
                'source': 'row:enroll:std_amount',
                'value_map': {'ENROLL': 'Employee Only'},
                'employee_only': True,
                'line': 'std',
            },
            {
                'header': 'Long Term Disability Coverage Type (Required if quoting product)',
                'source': 'row:enroll:ltd_amount',
                'value_map': {'ENROLL': 'Employee Only'},
                'employee_only': True,
                'line': 'ltd',
            },
        ],
        'group_info': [
            {
                'cell': 'A5',
                'label': '*Company Name',
                'sheet': 'Group Info',
                'source': 'group.legal_name',
                'label_cell': 'A4',
            },
            {
                'cell': 'B5',
                'label': '*Requested Effective Date',
                'sheet': 'Group Info',
                'source': 'deal.effective_date',
                'label_cell': 'B4',
            },
            {
                'cell': 'C5',
                'label': 'Primary Contact',
                'sheet': 'Group Info',
                'source': 'group.contact_first',
                'label_cell': 'C4',
            },
            {
                'cell': 'D5',
                'label': 'Primary Contact',
                'sheet': 'Group Info',
                'source': 'group.contact_last',
                'label_cell': 'D4',
            },
            {
                'cell': 'E5',
                'label': 'Primary Contact',
                'sheet': 'Group Info',
                'source': 'group.contact_email',
                'label_cell': 'E4',
            },
            {'cell': 'F5', 'label': '*SIC Code', 'sheet': 'Group Info', 'source': 'group.sic', 'label_cell': 'F4'},
            {
                'cell': 'H5',
                'label': '*Medical Funding Type',
                'sheet': 'Group Info',
                'source': 'rfp.funding_token',
                'label_cell': 'H4',
            },
            {
                'cell': 'I5',
                'label': '*Quote Medical Plans',
                'sheet': 'Group Info',
                'source': 'rfp.quote.medical',
                'label_cell': 'I4',
            },
            {
                'cell': 'J5',
                'label': '*Quote Dental Plans',
                'sheet': 'Group Info',
                'source': 'rfp.quote.dental',
                'label_cell': 'J4',
            },
            {
                'cell': 'K5',
                'label': '*Quote Vision Plans',
                'sheet': 'Group Info',
                'source': 'rfp.quote.vision',
                'label_cell': 'K4',
            },
            {
                'cell': 'L5',
                'label': '*Quote Life Plans',
                'sheet': 'Group Info',
                'source': 'rfp.quote.life',
                'label_cell': 'L4',
            },
            {
                'cell': 'M5',
                'label': '*Quote STD Plans',
                'sheet': 'Group Info',
                'source': 'rfp.quote.std',
                'label_cell': 'M4',
            },
            {
                'cell': 'N5',
                'label': '*Quote LTD Plans',
                'sheet': 'Group Info',
                'source': 'rfp.quote.ltd',
                'label_cell': 'N4',
            },
            {'cell': 'A13', 'label': '*Zip Code', 'sheet': 'Group Info', 'source': 'group.zip', 'label_cell': 'A12'},
            {
                'cell': 'B13',
                'label': '*Total Employees Applying',
                'sheet': 'Group Info',
                'source': 'group.enrolled',
                'label_cell': 'B12',
            },
            {
                'cell': 'C13',
                'label': '*Total Eligible Employees',
                'sheet': 'Group Info',
                'source': 'group.eligible',
                'label_cell': 'C12',
            },
            {
                'cell': 'D13',
                'label': '*Total Waiving Employees',
                'sheet': 'Group Info',
                'source': 'group.waiving',
                'label_cell': 'D12',
            },
            {'cell': 'E13', 'label': '*ATNE', 'sheet': 'Group Info', 'source': 'group.atne', 'label_cell': 'E12'},
            {'cell': 'F13', 'label': '*FTE', 'sheet': 'Group Info', 'source': 'group.fte', 'label_cell': 'F12'},
        ],
        'gaps': [
            {
                'header': 'Applicant Id',
                'home': 'never ours to fill',
                'note': "UHC's own identifier, and hidden in their sheet.",
            },
            {
                'header': 'Individual Applicant Id',
                'home': 'never ours to fill',
                'note': "UHC's own identifier, and hidden in their sheet.",
            },
            {
                'header': 'Special Employee',
                'home': 'census column',
                'note': 'K1 owners and contractors — a yes/no per person. The team asked for this one to stay '
                'OUT: "don’t want to ever capture special employee, leave it in the format but we don’t '
                'want it in our census" (2026-09-24). Still proposable, so the decision stays visible as '
                'a decision rather than disappearing from the list.',
            },
        ],
        'not_sent': {
            'banner': 'Employee Information - Quote',
            'unwritten_banner': 'Employee Information - Enrollment',
            'columns': [
                {
                    'letter': 'Y',
                    'header': '*Waive All Products?',
                    'formula': False,
                    'home': 'we already store it',
                    'note': 'We can answer this one without asking anybody — '
                    '`plan_math.waive_all_token` reads it off the tiers already on the roster '
                    '— and we deliberately do not send it at quote time. It is the first '
                    'column of their enrollment half, and the whole band is refilled after a '
                    'sale. Their own Z formula reads this cell, which is why it was worth '
                    'reaching for before the band boundary was understood.',
                },
                {
                    'letter': 'Z',
                    'header': '*Medical Plan',
                    'formula': True,
                    'fills': 'medical_plan',
                    'home': 'we already store it',
                    'note': 'The plan name we already carry on the roster. UHC wants their own plan '
                    'code here at enrollment, so our text may not be what they will accept.',
                },
                {
                    'letter': 'AA',
                    'header': 'I am waiving Medical Insurance for the following reason: (Required if '
                    'waiving Medical coverage)',
                    'formula': False,
                    'fills': 'waiver_reason',
                    'home': 'we already store it',
                    'note': 'The third name for one column: Warner calls it WAIVE REASON, UHC calls '
                    'it Medical Waiver Reason in the quote half (S) and this in the '
                    'enrollment half. It was the strongest case on this sheet — two carriers '
                    'asking, and a plain cell rather than one of their formulas — and it is '
                    'the one that got built. Written at S; blank here.',
                },
                {
                    'letter': 'AB',
                    'header': 'Does member want to Auto Assign PCP? (Required if medical plan requires PCP)',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': 'The member chooses their own PCP at enrollment.',
                },
                {
                    'letter': 'AC',
                    'header': 'Medical Plan PCP ID# (Required if medical plan requires PCP)',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': "UHC's own provider directory id.",
                },
                {
                    'letter': 'AD',
                    'header': 'Existing Patient (Required if not auto assigning PCP)',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': 'Only the member knows whether they already see that doctor.',
                },
                {
                    'letter': 'AE',
                    'header': '*Dental Plan',
                    'formula': True,
                    'fills': 'dental_plan',
                    'home': 'we already store it',
                    'note': 'As the medical plan column — ours is a name, theirs is a code assigned at sale.',
                },
                {
                    'letter': 'AF',
                    'header': '*Vision Plan',
                    'formula': True,
                    'fills': 'vision_plan',
                    'home': 'we already store it',
                    'note': 'As the medical plan column.',
                },
                {
                    'letter': 'AG',
                    'header': '*Basic Life Plan',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': "UHC's own plan code, assigned once the group buys. Our basic_life_amount "
                    'is a benefit amount, not their code.',
                },
                {
                    'letter': 'AH',
                    'header': '*Basic Dependent Life Plan Code',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': "UHC's own plan code.",
                },
                {
                    'letter': 'AI',
                    'header': 'Supplemental Life Plan Code',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': "UHC's own plan code.",
                },
                {
                    'letter': 'AJ',
                    'header': 'Supplemental Dependent Life Spouse Plan Code',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': "UHC's own plan code.",
                },
                {
                    'letter': 'AK',
                    'header': 'Supplemental Dependent Life Child Plan Code',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': "UHC's own plan code.",
                },
                {
                    'letter': 'AL',
                    'header': 'STD Plan Code',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': "UHC's own plan code.",
                },
                {
                    'letter': 'AM',
                    'header': 'LTD Plan Code',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': "UHC's own plan code.",
                },
                {
                    'letter': 'AN',
                    'header': 'Owner/Partner Not Covered by Workers Comp (optional)',
                    'formula': False,
                    'home': 'never ours to fill',
                    'note': "A statement about the employer's workers' comp policy, made per owner at enrollment.",
                },
                {
                    'letter': 'AO',
                    'header': '*# of Hours Worked',
                    'formula': True,
                    'fills': 'hours_per_week',
                    'home': 'we already store it',
                    'note': 'The same column Warner calls HOURS, and UHC marks it required. REQUIRED '
                    'on our census now, because FTE is counted from it and a blank costs a '
                    'group-size answer rather than just a cell. Written at Warner I; blank '
                    'here.',
                },
                {
                    'letter': 'AP',
                    'header': '*Date of Hire MM/DD/YYYY',
                    'formula': True,
                    'fills': 'hire_date',
                    'home': 'we already store it',
                    'note': 'On our census and on most payroll exports. Nothing stops us sending it '
                    'except that quoting does not need it.',
                },
                {
                    'letter': 'AQ',
                    'header': '*SSN ###-##-####',
                    'formula': True,
                    'fills': 'ssn',
                    'home': 'we already store it',
                    'note': 'Required on OUR census and required by UHC here — the pair the report '
                    'used to miss, and the reason its old headline ("no format has a writable '
                    'SSN column") was false. Two reasons it still does not go: it is the most '
                    'sensitive field on the roster, and their cell is a formula.',
                },
                {
                    'letter': 'AR',
                    'header': 'Reason SSN Not Provided (Required if no SSN)',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': 'Only asked when the member withholds an SSN, which happens on their own form, not ours.',
                },
                {
                    'letter': 'AS',
                    'header': '*Address 1',
                    'formula': True,
                    'fills': 'address1',
                    'home': 'we already store it',
                    'note': 'Home address. We hold it; a quote needs only the ZIP, which already goes out in column E.',
                },
                {
                    'letter': 'AT',
                    'header': 'Address 2',
                    'formula': True,
                    'fills': 'address2',
                    'home': 'we already store it',
                    'note': 'As Address 1.',
                },
                {
                    'letter': 'AU',
                    'header': 'City (optional)',
                    'formula': True,
                    'fills': 'city',
                    'home': 'we already store it',
                    'note': 'UHC marks it optional and derives it from the ZIP on upload, so sending '
                    'it would add nothing.',
                },
                {
                    'letter': 'AV',
                    'header': 'State (optional)',
                    'formula': True,
                    'fills': 'state',
                    'home': 'we already store it',
                    'note': 'As City — derived from the ZIP on their side.',
                },
                {
                    'letter': 'AW',
                    'header': '*ZIP (Zip Code entered will derive City & State after upload)',
                    'formula': True,
                    'fills': 'zip',
                    'home': 'we already store it',
                    'note': 'The same ZIP we already send in column E of the quote half. Their '
                    'enrollment half asks for it again.',
                },
                {
                    'letter': 'AX',
                    'header': '*County',
                    'formula': True,
                    'fills': 'county',
                    'home': 'we already store it',
                    'note': 'The same column Warner calls COUNTY, and UHC marks it required. An '
                    'optional column, derived from the ZIP at export when nobody typed one — '
                    'a typed county always wins, because a crosswalk cannot know a county '
                    'line moved. Written at Warner H; blank here.',
                },
                {
                    'letter': 'AY',
                    'header': 'Email',
                    'formula': True,
                    'fills': 'email',
                    'home': 'we already store it',
                    'note': 'The same column as UHC O in the quote half, which we now write. Blank here.',
                },
                {
                    'letter': 'AZ',
                    'header': 'Phone Number',
                    'formula': True,
                    'fills': 'phone',
                    'home': 'we already store it',
                    'note': 'On our census since the 2026-08 census-depth pass and read by no format today.',
                },
                {
                    'letter': 'BA',
                    'header': 'Phone Type',
                    'formula': True,
                    'home': 'census column',
                    'note': 'Home / Mobile / Work, from their own dropdown. Only worth a column if we '
                    'decide to send the phone number at all.',
                },
                {
                    'letter': 'BB',
                    'header': 'Height - Feet (Level Funded Only)',
                    'formula': True,
                    'home': 'census column',
                    'note': 'Level-funded underwriting. UHC splits height into feet and inches; one '
                    'column of ours would serve both.',
                },
                {
                    'letter': 'BC',
                    'header': 'Height - Inches (Level Funded Only)',
                    'formula': True,
                    'home': 'census column',
                    'note': 'The inches half of the same question as BB.',
                },
                {
                    'letter': 'BD',
                    'header': 'Weight (Level Funded Only)',
                    'formula': True,
                    'home': 'census column',
                    'note': 'Level-funded underwriting, per member.',
                },
                {
                    'letter': 'BE',
                    'header': 'Tobacco (Level Funded Only)',
                    'formula': True,
                    'home': 'census column',
                    'note': 'Level-funded underwriting. Aetna’s SMART census asks for it too, so it '
                    'is not UHC-specific.',
                },
                {
                    'letter': 'BF',
                    'header': '*On the day this coverage begins, will you, your spouse or any of your '
                    'dependents be covered under any other medical health plan or policy '
                    'including another UnitedHealthcare plan or Medicare?',
                    'formula': False,
                    'home': 'never ours to fill',
                    'note': 'Other-coverage attestation. The member answers it and signs for it at enrollment.',
                },
                {
                    'letter': 'BG',
                    'header': 'Name of Other Carrier (Required if employee or dependent covered by another plan',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': 'Follows BF, and only the member can answer it.',
                },
                {
                    'letter': 'BH',
                    'header': '*Medicare Primary?',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': 'Medicare coordination, established with the member at enrollment.',
                },
                {
                    'letter': 'BI',
                    'header': 'Medicare Reason (Required if Medicare Primary)',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': 'Follows BH.',
                },
                {
                    'letter': 'BJ',
                    'header': 'Medicare Claim Number (Required if Medicare Primary)',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': "The member's own Medicare claim number.",
                },
                {
                    'letter': 'BK',
                    'header': 'Medicare Part A Start Date (Required if Medicare Primary)',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': 'Follows BH.',
                },
                {
                    'letter': 'BL',
                    'header': 'Medicare Part B Start Date (Required if Medicare Primary)',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': 'Follows BH.',
                },
                {
                    'letter': 'BM',
                    'header': 'Medicare Part D Start Date (Required if Medicare Primary)',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': 'Follows BH.',
                },
                {
                    'letter': 'BN',
                    'header': 'COBRA Start Date (Required if COBRA)',
                    'formula': True,
                    'home': 'census column',
                    'note': 'Our employment_status can say COBRA; it holds no dates. Both Warner and '
                    'Aetna ask for the status, only UHC for the dates.',
                },
                {
                    'letter': 'BO',
                    'header': 'COBRA End Date (Required if COBRA)',
                    'formula': True,
                    'home': 'census column',
                    'note': 'The other half of BN.',
                },
                {
                    'letter': 'BP',
                    'header': '*Is dependent permanently disabled?',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': 'A disabled-dependent certification the family makes, with medical '
                    'evidence, at enrollment.',
                },
                {
                    'letter': 'BQ',
                    'header': 'Mental or Physical? (Required if dependent permanently disabled)',
                    'formula': True,
                    'home': 'never ours to fill',
                    'note': 'Follows BP.',
                },
                {
                    'letter': 'BR',
                    'header': 'Is dependent an Illinois resident? (Required if employer primary '
                    'location is in Illinois)',
                    'formula': False,
                    'home': 'never ours to fill',
                    'note': 'An Illinois-only dependent question, asked of the family at enrollment.',
                },
                {
                    'letter': 'BS',
                    'header': 'Has dependent served as an active or a reserve member of an US Armed '
                    'Forces and received a release or discharge other than a dishonorable '
                    'discharge? (Required if employer primary location is in Illinois)',
                    'formula': False,
                    'home': 'never ours to fill',
                    'note': 'An Illinois-only veteran-dependent question.',
                },
                {
                    'letter': 'BT',
                    'header': 'Is dependent an unmarried, Florida resident? (Required if employer '
                    'primary location is in Florida)',
                    'formula': False,
                    'home': 'never ours to fill',
                    'note': 'A Florida-only dependent question.',
                },
                {
                    'letter': 'BU',
                    'header': 'Is dependent child a full time student? (Required if employer primary '
                    'location is in Iowa)',
                    'formula': False,
                    'home': 'never ours to fill',
                    'note': 'An Iowa-only dependent question.',
                },
                {
                    'letter': 'BV',
                    'header': 'Does the dependent meet all of the following criteria: unmarried, '
                    'resident of Pennsylvania or enrolled as a full-time student, with no '
                    'dependents and not covered under another health insurance plan. '
                    '(Required if employer primary location is in Pennsylvania)',
                    'formula': False,
                    'home': 'never ours to fill',
                    'note': 'A Pennsylvania-only dependent question.',
                },
                {
                    'letter': 'BW',
                    'header': "Worker's Comp (Required if worker's comp coverage is yes)",
                    'formula': False,
                    'home': 'never ours to fill',
                    'note': "A statement about the employer's workers' comp coverage for that person.",
                },
                {
                    'letter': 'BX',
                    'header': 'Member ID',
                    'formula': False,
                    'home': 'never ours to fill',
                    'note': "UHC's own member id, issued after enrollment.",
                },
            ],
        },
    },
}

UNIVERSAL = 'warner_census'  # Warner Pacific's census: the file any carrier without its own format receives (K39)
ORDER = tuple(DEFINITIONS)
BY_FILE_KEY = {found['file_key']: found for found in DEFINITIONS.values()}
