# Permission Justification for Meta App Review

**App Name**: Doctor Calendar Instagram Automation
**Use Case**: Automated Instagram Story posting of clinic doctor schedules (3 posts/day)

---

## `instagram_business_basic`

**Permission Description**: Allows the app to read basic profile information of the connected Instagram Business Account.

**Justification**:

Our application, Doctor Calendar, automates the posting of daily doctor schedule information to a medical clinic's official Instagram Business Account. We use the `instagram_business_basic` permission to verify the connected Instagram Business Account ID and confirm that the authenticated account is a valid business profile before initiating any content publishing operations. This permission is essential to ensure that our automated posting system is properly linked to the correct clinic account, preventing accidental publishing to unintended accounts. The profile information retrieved is used solely for account validation purposes and is never stored beyond the active session or shared with third parties.

---

## `instagram_business_content_publish`

**Permission Description**: Allows the app to create and publish content (photos and Stories) on behalf of the connected Instagram Business Account.

**Justification**:

Our application uses the `instagram_business_content_publish` permission to automatically post doctor schedule information as Instagram Stories on behalf of a medical clinic. The clinic operates with multiple doctors on rotating schedules, and timely communication of these schedules to patients is critical for appointment planning. Each day, the system reads the doctor's attendance data from a clinic-managed Google Spreadsheet, generates an informational image displaying the day's available doctors and their working hours, and publishes it as an Instagram Story via the Content Publish API. This process runs up to three times per day (morning, midday, and evening updates) to keep patients informed of any schedule changes. The permission is used exclusively for this automated scheduling use case, and no user-generated content or third-party data is published through this permission. All published content is clinic-managed and reviewed by clinic administrators.

---

## Summary of Data Handling

| Data Type | Purpose | Retention |
|-----------|---------|-----------|
| Instagram Business Account ID | Account validation before posting | Session only, not persisted |
| Access Token | API authentication | Stored securely in server environment variable |
| Doctor schedule data | Source data for image generation | Managed by clinic in Google Spreadsheet |
| Published image content | Daily schedule notification to patients | Clinic-owned; managed by Instagram's standard retention |

All data handling complies with Meta's Platform Terms and Developer Policies. The application does not collect, store, or process any Instagram user data beyond what is necessary for the described automated posting functionality.
