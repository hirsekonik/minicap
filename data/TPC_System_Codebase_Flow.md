# TPC WEB-BASED STUDENT CLEARANCE SYSTEM — EXACT CODEBASE ARCHITECTURE, ROUTES, CONTROLLERS & WORKFLOWS

## 1. Technical Stack & Real-Time Architecture
- **Backend Framework**: Laravel 11 (PHP 8.2+) with Eloquent ORM, Role-Based Access Control (RBAC) middleware (`role:student`, `role:staff`, `role:admin`, `role:president`), and Laravel Fortify authentication.
- **Frontend Stack**: Vue 3 (Composition API, `<script setup lang="ts">`), Inertia.js, Tailwind CSS, and Lucide Icons.
- **Real-Time Dashboard Synchronization**: The Student Dashboard (`resources/js/pages/Dashboard.vue`) runs an automatic 5-second Inertia polling loop (`setInterval(..., 5000)`) that reloads `clearanceRequest`, `offices`, `notifications`, `studentClearance`, `clearanceStatus`, and `clearanceNotice` without refreshing the browser.
- **PDF & Anti-Fraud QR Engine**: Uses `barryvdh/laravel-dompdf` (DomPDF) to generate downloadable A4 portrait PDF Clearance Receipts and `bacon/bacon-qr-code` (SVG backend) to embed a scannable verification QR code linking to `/verify-clearance/{verificationCode}`.

## 2. Official 7 Academic Courses (`CourseSeeder.php`)
1. **BSIS** — Bachelor of Science in Information System
2. **BAEL** — Bachelor of Arts in English Language
3. **BAPS** — Bachelor of Science in Political Science
4. **BSA** — Bachelor of Science in Agriculture
5. **BSAIS** — Bachelor of Science in Accounting Information System
6. **BECED** — Bachelor of Early Childhood Education
7. **BSCRIM** — Bachelor of Science in Criminology

## 3. Official 14 Signatory Offices & Exact Sort Order (`OfficeSeeder.php`)
Every course (`CourseOfficeSeeder.php`) is mapped to the 13 regular clearance offices (`is_final_approver = false`), followed by the 14th office (`Office of the College President`, `is_final_approver = true`).
Offices are dynamically sorted on the dashboard using `Office::sortByPrerequisites()` (topological sort by prerequisite depth first, then `sort_order`, with `is_final_approver` always placed last at depth 99999).

### Group A: Student Services (Sort Order 1 to 9)
1. **Guidance Office** (`sort_order: 1`, `group: Student Services`, `is_final_approver: false`) — Counseling records, exit interview, and guidance clearance.
2. **Medical-Dental Clinic** (`sort_order: 2`, `group: Student Services`, `is_final_approver: false`) — Health records and clinic clearance.
3. **Library** (`sort_order: 3`, `group: Student Services`, `is_final_approver: false`) — Book returns, borrower's card, and settlement of library fines.
4. **Security and Safety Office** (`sort_order: 4`, `group: Student Services`, `is_final_approver: false`) — Campus safety compliance, ID/parking, and violation records.
5. **Equipment and Facilities** (`sort_order: 5`, `group: Student Services`, `is_final_approver: false`) — Laboratory apparatus, tools, and borrowed campus equipment (Property Custodian).
6. **Supreme Student Government (SSG)** (`sort_order: 6`, `group: Student Services`, `is_final_approver: false`) — Student council dues, event attendance, and officer turnover/liquidation.
7. **PE/Sports** (`sort_order: 7`, `group: Student Services`, `is_final_approver: false`) — Athletics gear, sports uniforms, and PE equipment clearance.
8. **Canteen** (`sort_order: 8`, `group: Student Services`, `is_final_approver: false`) — Settlement of any outstanding meal or canteen balances.
9. **Registrar** (`sort_order: 9`, `group: Student Services`, `is_final_approver: false`) — Academic records, grades submission, Form 137/credentials, and academic units verification.

### Group B: Offices and Administration (Sort Order 10 to 14)
10. **Program Head** (`sort_order: 10`, `group: Offices and Administration`, `is_final_approver: false`) — Department requirements and hardbound Capstone/Thesis submission.
11. **Office of Student Affairs and Services (OSAS)** (`sort_order: 11`, `group: Offices and Administration`, `is_final_approver: false`) — Disciplinary clearance, Good Moral eligibility, and mandatory Student ID surrender.
12. **Office of the Vice President for Academic Affairs** (`sort_order: 12`, `group: Offices and Administration`, `is_final_approver: false`) — Academic affairs compliance validation (VPAA).
13. **Office of the Vice President for Administration** (`sort_order: 13`, `group: Offices and Administration`, `is_final_approver: false`) — Administrative and financial compliance sign-off (VPA).
14. **Office of the College President** (`sort_order: 14`, `group: Offices and Administration`, `is_final_approver: true`) — Sole Final Executive Approver that unlocks the printable Clearance Receipt & PDF Certificate.

## 4. Exact Controller Logic & Status State Machine

### A. Student Clearance Flow (`App\Http\Controllers\Student\ClearanceRequestController` & `Dashboard.vue`)
- **Student Dashboard Summary Cards**: Displays 4 metric cards: **Approved** count, **Pending** count, **Not Cleared** count (`offices.length - approvedCount`), and **Final Status** (`Not Started`, `In Progress`, or `Fully Approved`), plus an **Overall Progress Percentage Bar** (`0%` to `100%`).
- **Clearance Period Gatekeeper**: Both `store()` (`POST /student/clearance-requests`) and `requestMoreOffices()` (`PATCH /student/clearance-requests/request-more-offices`) check `AppSetting::get('clearance_status', 'open') !== 'open'`. If closed, the system blocks submission with: *"Clearance submissions are currently closed. The administration has not opened the clearance period yet."*
- **Initial Submission (`POST /student/clearance-requests`)**:
  - Student clicks **"Submit Clearance Request"** on `/dashboard` (or `?view=request`), selects available offices (or clicks **"Select All Available"**), and submits.
  - Creates one `ClearanceRequest` record for the student's `user_id`, active `semester`, and `school_year` with overall `status = 'pending'` and `submitted_at = now()`.
  - Creates `ClearanceApproval` rows for all 14 offices: selected offices with 0 prerequisites get `status = 'pending'`, while unselected or prerequisite-locked offices get `status = 'not_requested'`.
  - Sends in-app notifications (`NotificationService::send`) to active staff assigned to the requested offices.
- **Requesting Newly Unlocked Offices (`PATCH /student/clearance-requests/request-more-offices`)**:
  - As prerequisite offices approve the student's clearance, dependent offices automatically unlock on the dashboard (via 5-second real-time polling).
  - Student clicks **"Request More Offices"** (or **"Request Final Approval"** once all 13 regular offices are approved).
  - Controller validates that every prerequisite in `office->prerequisites` is already in `approved` status.
  - For the final approver (`Office of the College President`, `is_final_approver = true`), validates that **every single regular office (all 13 regular offices)** assigned to the student's course has `status === 'approved'`. If not, returns: *"You must clear all regular offices before requesting final approval."*
  - Updates matching `not_requested` rows to `pending` and notifies the target office staff (or President at `/president/final-approvals`).
- **Handling Rejections & Re-Evaluation (`PATCH /student/clearance-approvals/{approval}/mark-as-complied`)**:
  - If an office rejects a request, the office card turns red (`rejected`) and displays the mandatory staff **Remarks** explaining the exact deficiency.
  - Only items with `status === 'rejected'` can be marked as complied.
  - After settling the obligation with the office, the student clicks **"Mark as Complied"** on the rejected office card.
  - This resets `status` from `'rejected'` back to `'pending'`, clears `approved_by = null` and `acted_at = null`, and sends a `'Clearance marked as complied'` notification to the office staff so they can re-evaluate and approve it.

### B. Office Staff Signatory Flow (`App\Http\Controllers\Staff\PendingRequestController`)
- **Route**: `GET /staff/pending-requests`
- **Strict Department Isolation**: Staff only see `ClearanceApproval` rows where `office_id === $user->office_id` and `status` is in `['pending', 'approved', 'rejected']` for the active semester and school year.
- **Single Approve (`PATCH /staff/clearance-approvals/{approval}/approve`)**: Sets `status = 'approved'`, `approved_by = $user->id`, `remarks = null`, `acted_at = now()`, and notifies the student (`'Clearance request approved'`).
- **Bulk Approve All (`PATCH /staff/clearance-approvals/approve-all`)**: Approves all currently `'pending'` requests for that staff member's assigned office in one click and notifies each student.
- **Reject with Mandatory Remarks (`PATCH /staff/clearance-approvals/{approval}/reject`)**: Validates `'remarks' => ['required', 'string', 'max:1000']`, sets `status = 'rejected'`, saves `remarks`, `approved_by`, and `acted_at`, and notifies the student (`'Clearance request rejected'`).
- **Staff Mark as Complied (`PATCH /staff/clearance-approvals/{approval}/mark-as-complied`)**: Allows office staff to directly move a `'rejected'` item back to `'pending'` on behalf of a student who settled their deficiency in person.

### C. College President Final Approval Flow (`App\Http\Controllers\President\FinalApprovalController`)
- **Route**: `GET /president/final-approvals`
- **Ready Queue Rule (`isReadyForFinalApproval`)**: A student's clearance request is ready for final approval if and only if:
  1. All non-final-approver (`is_final_approver = false`) office approvals (all 13 regular offices) are `'approved'`.
  2. The President (`is_final_approver = true`) approval row is `'pending'`.
  3. The parent `ClearanceRequest` status is not yet `'cleared'`.
- **Final Approval & Receipt Generation (`finalizeClearanceRequest`)**:
  - Triggered by single **"Approve"** (`PATCH /president/final-approvals/{clearanceRequest}/approve`) or bulk **"Auto Approve All Ready"** (`PATCH /president/final-approvals/approve-all`).
  - Sets President approval to `'approved'`, updates parent `ClearanceRequest` to `status = 'cleared'` and `cleared_at = now()`.
  - Generates the official **Receipt Number** in the exact format `TPC-CLR-YYYY-XXXXXX` (e.g., `TPC-CLR-2026-000042`, using `sprintf('TPC-CLR-%s-%06d', now()->format('Y'), $clearanceRequest->id)`).
  - Generates a unique 32-character uppercase alphanumeric **Verification Code** (`Str::upper(Str::random(32))`).
  - Sends a `'Clearance Fully Approved'` notification to the student.
- **President Reject / Mark as Complied**: The President can also reject a final request with mandatory `remarks` (`PATCH /president/final-approvals/{clearanceRequest}/reject`) or mark a rejected final request as complied (`PATCH /president/final-approvals/{clearanceRequest}/mark-as-complied`).

### D. Official Clearance Receipt & Public QR Verification (`ClearanceReceiptController` & `ClearanceVerificationController`)
- **View Printable Receipt**: `GET /clearance-receipts/{clearanceRequest}` (accessible by the student owner, `admin`, or `president` only after `status === 'cleared'`).
- **Download Official PDF Receipt**: `GET /clearance-receipts/{clearanceRequest}/download` generates `clearance-receipt-{receipt_number}.pdf` (A4 portrait) containing the TPC header, Receipt Number, Student Info, full 13-office approval table with Approver Name & Date Approved, Final Approval table, 32-character Verification Code, Verification URL, and scannable SVG QR Code.
- **Public Anti-Fraud QR Verification**: `GET /verify-clearance/{verificationCode}` is a public route (no login required) that verifies the cryptographic code against the live database and displays a green **VALID AND FULLY CLEARED** badge or an invalid/unverified warning.

### E. OSAS Administrator Flow (`App\Http\Controllers\Admin\*`)
- **Admin Dashboard (`/admin/dashboard`)**: Institutional KPI metrics (`Total Students`, `Submitted Requests`, `Fully Cleared`, `Pending Requests`) and Department Bottleneck Analysis.
- **User Management (`/admin/users`)**: Create/edit Student, Staff, President, and Admin accounts; assign courses or offices; activate/deactivate accounts (`PATCH /admin/users/{user}/toggle-active`).
- **Course Modules (`/admin/course-modules`)**: Configure which regular offices are required for each academic course.
- **Office Prerequisites (`/admin/office-prerequisites`)**: Configure prerequisite dependencies between offices (e.g., requiring Library, Guidance, PE/Sports, Canteen, SSG, etc. before Registrar or OSAS).
- **Master Clearance Requests Audit (`/admin/clearance-requests`)**: Inspect any student's granular 14-office approval timeline.
- **Reports & Exports (`/admin/reports`)**: Filter institutional clearance data, export to CSV (`/admin/reports/export-csv`), or open the formatted Printable Report (`/admin/reports/print`).
- **System Settings (`/admin/settings`)**:
  - **Clearance Period Control (`PATCH /admin/settings/clearance-status`)**: Start (`open`) or Stop (`closed`) student clearance submissions and broadcast a custom `clearance_notice` banner across all student dashboards.
  - **Academic Term Cycling (`PATCH /admin/settings`)**: Switch `active_semester` (`1st Semester`, `2nd Semester`, `Summer`) and `active_school_year`. Requires typing `RESET CLEARANCES` in the confirmation modal. Historical records remain safely stored in the database while starting a fresh cycle for the new term.

---

# TALIBON POLYTECHNIC COLLEGE
## Web-Based Student Clearance System with Role-Based Approval
### **Official Comprehensive System User Manual**

---

## Document Control & Information

| Document Attribute | Specification |
| :--- | :--- |
| **System Title** | Web-Based Student Clearance System with Role-Based Approval |
| **Institution** | Talibon Polytechnic College (TPC) |
| **Campus Location** | San Isidro, Talibon, Bohol, Philippines |
| **Document Version** | 1.0 (Production Release) |
| **Target Audience** | Students, Office Staff / Signatories, College President, System Administrators (OSAS), and Academic Verifiers |
| **Technology Stack** | Laravel 11, Inertia.js, Vue 3, Tailwind CSS, MySQL, DomPDF, BaconQrCode |

---

# Table of Contents
1. [Part 1: General System Overview & Getting Started](#part-1-general-system-overview--getting-started)
   - [1.1 Background and Institutional Context](#11-background-and-institutional-context)
   - [1.2 Objectives & Key Benefits](#12-objectives--key-benefits)
   - [1.3 Core Security & Data Integrity Features](#13-core-security--data-integrity-features)
   - [1.4 System Architecture & Technical Specifications](#14-system-architecture--technical-specifications)
   - [1.5 User Roles & Permissions Matrix](#15-user-roles--permissions-matrix)
   - [1.6 Getting Started & Authentication](#16-getting-started--authentication)
2. [Part 2: Student User Manual](#part-2-student-user-manual)
   - [2.1 Navigating the Student Dashboard](#21-navigating-the-student-dashboard)
   - [2.2 Step 1: Submitting an Initial Clearance Request](#22-step-1-submitting-an-initial-clearance-request)
   - [2.3 Step 2: Understanding Sequential Prerequisites](#23-step-2-understanding-sequential-prerequisites)
   - [2.4 Step 3: Requesting Newly Unlocked Offices](#24-step-3-requesting-newly-unlocked-offices)
   - [2.5 Step 4: Tracking Real-Time Status & Notifications](#25-step-4-tracking-real-time-status--notifications)
   - [2.6 Step 5: Handling Deficiencies & Rejections (Compliance Workflow)](#26-step-5-handling-deficiencies--rejections-compliance-workflow)
   - [2.7 Step 6: Requesting College President Final Clearance](#27-step-6-requesting-college-president-final-clearance)
   - [2.8 Step 7: Viewing & Printing Official Clearance Receipt](#28-step-7-viewing--printing-official-clearance-receipt)
   - [2.9 Step 8: Downloading the Official PDF Certificate](#29-step-8-downloading-the-official-pdf-certificate)
3. [Part 3: Office Staff & Department Signatory Manual](#part-3-office-staff--department-signatory-manual)
   - [3.1 Staff Dashboard & Pending Requests Queue](#31-staff-dashboard--pending-requests-queue)
   - [3.2 Filtering, Searching, and Sorting Students](#32-filtering-searching-and-sorting-students)
   - [3.3 Approving an Individual Clearance Request](#33-approving-an-individual-clearance-request)
   - [3.4 Bulk Clearance Approvals ("Approve All")](#34-bulk-clearance-approvals-approve-all)
   - [3.5 Rejecting Clearances with Mandatory Deficiency Remarks](#35-rejecting-clearances-with-mandatory-deficiency-remarks)
   - [3.6 Marking as Complied on Behalf of Students](#36-marking-as-complied-on-behalf-of-students)
4. [Part 4: College President (Final Approver) Manual](#part-4-college-president-final-approver-manual)
   - [4.1 Executive Final Approvals Portal](#41-executive-final-approvals-portal)
   - [4.2 Ready-for-Final-Approval Queue Logic](#42-ready-for-final-approval-queue-logic)
   - [4.3 Inspecting Departmental Audit Trails](#43-inspecting-departmental-audit-trails)
   - [4.4 Granting Final Approval (Individual & Bulk)](#44-granting-final-approval-individual--bulk)
   - [4.5 Generating Official Receipt Numbers & Cryptographic Verification Tokens](#45-generating-official-receipt-numbers--cryptographic-verification-tokens)
   - [4.6 Handling Presidential Rejections & Compliance Holds](#46-handling-presidential-rejections--compliance-holds)
5. [Part 5: System Administrator & OSAS Director Manual](#part-5-system-administrator--osas-director-manual)
   - [5.1 Administrative Analytics Dashboard](#51-administrative-analytics-dashboard)
   - [5.2 User Management & Staff Provisioning](#52-user-management--staff-provisioning)
   - [5.3 Course Modules & Signatory Office Configuration](#53-course-modules--signatory-office-configuration)
   - [5.4 Office Prerequisites Configuration](#54-office-prerequisites-configuration)
   - [5.5 Academic Term Settings & Clearance Cycle Cycling](#55-academic-term-settings--clearance-cycle-cycling)
   - [5.6 Clearance Requests Master Audit View](#56-clearance-requests-master-audit-view)
   - [5.7 Official Clearance Reports, Analytics & Exports](#57-official-clearance-reports-analytics--exports)
6. [Part 6: Public Verification, Troubleshooting & Support](#part-6-public-verification-troubleshooting--support)
   - [6.1 Public Verification Portal Overview](#61-public-verification-portal-overview)
   - [6.2 QR Code Scanning & Direct Verification](#62-qr-code-scanning--direct-verification)
   - [6.3 Interpreting Verification States (Valid vs. Invalid)](#63-interpreting-verification-states-valid-vs-invalid)
   - [6.4 Common Student Questions & Solutions](#64-common-student-questions--solutions)
   - [6.5 Common Staff & Approver Questions](#65-common-staff--approver-questions)
   - [6.6 Common Administrative Questions](#66-common-administrative-questions)
   - [6.7 Technical Support & Escalation Channels](#67-technical-support--escalation-channels)

---

# Part 1: General System Overview & Getting Started

### 1.1 Background and Institutional Context
At **Talibon Polytechnic College (TPC)**, student clearance is a mandatory academic requirement conducted at the close of every semester and summer term. Historically, students navigated a manual, paper-based clearance system that required physical circulation across multiple campus offices. This traditional routine created congested queues, heightened document loss risks, caused administrative delays for graduating and enrolling students, and placed excessive logistical burdens on signatories.

The **Web-Based Student Clearance System with Role-Based Approval** transforms this multi-day in-person process into a centralized, transparent, and completely paperless digital clearance workflow.

### 1.2 Objectives & Key Benefits
- **Elimination of Physical Bottlenecks**: Students can submit clearance requests and monitor their signatory status 24/7 from any smartphone, tablet, or desktop computer.
- **Administrative Clearance Period Control**: OSAS administrators can start and stop the clearance period on-demand, locking premature student submissions outside official clearance schedules.
- **Strict Role-Based Enforcement**: Clear functional boundaries ensure that only designated signatories can review, approve, or reject submissions for their respective departments.
- **Hierarchical Prerequisite Control**: Administrative rules automatically prevent students from jumping ahead to dependent offices until prerequisite obligations (e.g., library books or canteen balances) are resolved.
- **Accountability & Deficiency Transparency**: Rejections require precise written remarks, letting students know exactly what deficiency exists and allowing immediate online or offline compliance.
- **Two-Tier Final Authorization**: Full institutional clearance requires sign-off from all departmental offices before graduating to the College President's final authorization.
- **Anti-Fraud Digital Verification**: Fully cleared students receive an official digital receipt containing a system-generated Receipt Number (`TPC-CLR-YYYY-XXXXXX`) and an encoded QR code for instant public verification.

### 1.3 Core Security & Data Integrity Features
1. **Role-Based Access Control (RBAC)**: Enforced via Laravel route middleware (`role:student`, `role:staff`, `role:president`, `role:admin`), guaranteeing users cannot perform actions outside their assigned privileges.
2. **Deterministic Prerequisite Verification**: Backend transactional checks prevent bypassing prerequisites even if direct API calls are attempted.
3. **Audit Trail Logging**: Every approval, rejection, and compliance update records the responsible user's primary key (`approved_by`), action timestamp (`acted_at`), and status remarks.
4. **Cryptographic Verification Codes**: Every cleared certificate receives a unique, collision-resistant 32-character token tied directly to the database record.
5. **Real-Time Synchronous Polling**: The frontend interfaces leverage an active 5-second polling cycle, instantly reflecting changes without requiring manual browser refreshes.

### 1.4 System Architecture & Technical Specifications

```
+-----------------------------------------------------------------------------+
|                               Client Layer                                  |
|  [Desktop Browsers]   [Mobile Smart Devices]   [Public QR Scanners / Camera]|
+-----------------------------------------------------------------------------+
                                       │ HTTPS
+-----------------------------------------------------------------------------+
|                         Frontend Presentation Layer                         |
|     Vue 3 (Composition API)  •  Inertia.js  •  Tailwind CSS  •  Lucide Icons  |
+-----------------------------------------------------------------------------+
                                       │ Inertia State / JSON
+-----------------------------------------------------------------------------+
|                         Backend Application Layer                           |
|      Laravel 11  •  Fortify Auth  •  DomPDF Engine  •  BaconQrCode          |
+-----------------------------------------------------------------------------+
                                       │ Eloquent ORM
+-----------------------------------------------------------------------------+
|                            Database Persistence                             |
|         MySQL 8.0 (Users, Clearance Requests, Approvals, Settings)          |
+-----------------------------------------------------------------------------+
```

### 1.5 User Roles & Permissions Matrix

### 2.1 Summary of User Roles

1. **Student**
   - The primary applicant. Registers their student ID, selects their enrolled academic program, submits clearance requests, complies with deficiency remarks, and prints/downloads the clearance receipt.
2. **Office Staff / Signatory**
   - Designated signatories for 13 campus departments. Reviews clearance requests assigned to their office, verifies student clearance obligations, approves or rejects with remarks, and records compliance.
3. **College President (Final Approver)**
   - The chief executive authority. Reviews students who have obtained 100% approval across all 13 regular offices and grants the final institutional clearance that generates the verified receipt.
4. **Administrator / OSAS Director**
   - The institutional supervisor from the Office of Student Affairs and Services. Manages user accounts, configures academic course-to-office mappings, maintains office prerequisite hierarchies, manages term cycles, and generates institutional reports.
5. **Public Verifier**
   - Any external party (employer, registrar officer, scholarship coordinator) who scans the QR code or enters the verification code to authenticate a student's clearance status.

### 2.2 Detailed Permissions Matrix

| Capability / System Action | Student | Staff | President | Admin | Public |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Self-Registration via Web Portal | **Yes** | No | No | No | No |
| Account Login & Session Authentication | **Yes** | **Yes** | **Yes** | **Yes** | No |
| View Personal Clearance Dashboard | **Yes** | No | No | No | No |
| Submit Initial Clearance Request | **Yes** | No | No | No | No |
| Request Subsequent Unlocked Offices | **Yes** | No | No | No | No |
| Submit Compliance on Rejected Items | **Yes** | No | No | No | No |
| View Assigned Office Pending Queue | No | **Yes** | No | No | No |
| Filter & Search Students in Queue | No | **Yes** | **Yes** | **Yes** | No |
| Approve Single Departmental Request | No | **Yes** | No | No | No |
| Bulk Approve Departmental Requests | No | **Yes** | No | No | No |
| Reject Request with Mandatory Remarks | No | **Yes** | **Yes** | No | No |
| Mark Deficiencies as Complied | No | **Yes** | **Yes** | No | No |
| Access Final Approvals Queue | No | No | **Yes** | No | No |
| Grant Final Clearance & Issue Receipt | No | No | **Yes** | No | No |
| View/Print Cleared Receipt & QR Code | **Yes (Own)**| No | **Yes** | **Yes** | No |
| Download Official PDF Certificate | **Yes (Own)**| No | **Yes** | **Yes** | No |
| Create/Edit Staff Accounts | No | No | No | **Yes** | No |
| Activate / Deactivate User Accounts | No | No | No | **Yes** | No |
| Assign Required Offices to Courses | No | No | No | **Yes** | No |
| Configure Office Prerequisites Chain | No | No | No | **Yes** | No |
| Switch Semester & School Year Terms | No | No | No | **Yes** | No |
| Start / Stop Clearance Period Window | No | No | No | **Yes** | No |
| Broadcast Dashboard Notice to Students | No | No | No | **Yes** | No |
| Generate & Export Official Reports | No | No | No | **Yes** | No |
| Scan QR Code & Publicly Verify Record| **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |

### 1.6 Getting Started & Authentication

### 3.1 System Access Prerequisites & Hardware Requirements

#### Client Workstation / Mobile Device Specifications
- **Operating System**: Windows 10/11, macOS, Linux, Android 9.0+, or iOS 13.0+.
- **Web Browser**: Google Chrome (v100+), Mozilla Firefox (v100+), Apple Safari (v14+), or Microsoft Edge (v100+). JavaScript must be enabled.
- **Network**: Stable broadband or 4G/5G mobile data connection (minimum 256 Kbps recommended).
- **PDF Viewer**: Adobe Acrobat Reader or any modern browser with integrated PDF viewing support.

### 3.2 Landing Page Navigation
Upon navigating to the base system address (`https://[domain-or-local-ip]/`), the system displays the official **Talibon Polytechnic College Student Clearance Portal** landing page.

- **Navigation Header**: Contains the official TPC emblem, institutional heading, and direct buttons for **Log In** and **Register**.
- **Hero Call-to-Action**: Highlights the current active academic term and provides a direct gateway for students to initiate or verify their clearance status.
- **Workflow Highlights**: Outlines the 4-step clearance workflow: (1) Submit Request, (2) Office Approvals, (3) President Sign-Off, (4) Get QR Receipt.

### 3.3 Student Account Self-Registration
Students who do not yet have an account must self-register using their authentic institutional credentials.

```
[Landing Page] ──> Click "Register" ──> Fill Form ──> Submit ──> Redirect to Student Dashboard
```

#### Step-by-Step Student Registration Procedure:
1. On the landing page or login view, click the **"Create an account"** or **"Register"** button.
2. Complete the registration form fields:
   - **Student ID**: Enter your official TPC Student ID Number (e.g., `2023-00123`). This must be unique.
   - **Full Name**: Enter your complete legal name (Last Name, First Name, Middle Name).
   - **Enrolled Course**: Select your degree program from the dropdown:
     * *BSIS* – Bachelor of Science in Information System
     * *BAEL* – Bachelor of Arts in English Language
     * *BAPS* – Bachelor of Science in Political Science
     * *BSA* – Bachelor of Science in Agriculture
     * *BSAIS* – Bachelor of Science in Accounting Information System
     * *BECED* – Bachelor of Early Childhood Education
     * *BSCRIM* – Bachelor of Science in Criminology
   - **Year Level**: Select your current year standing (*1st Year*, *2nd Year*, *3rd Year*, or *4th Year*).
   - **Email Address**: Enter a valid, active email address for clearance communications.
   - **Password**: Create a secure password (minimum 8 characters).
   - **Confirm Password**: Re-enter the exact same password.
3. Click **"Register"**. The system validates your data, provisions your student profile, and automatically logs you in to the **Student Dashboard**.

> [!NOTE]
> Staff, Administrator, and Presidential accounts are provisioned exclusively by the System Administrator and cannot be self-registered.

### 3.4 User Login & Multi-Role Redirection
1. Navigate to the login route (`/login`).
2. Input your registered **Student ID or Email Address** and your confidential **Password**.
3. (Optional) Check **"Remember me"** if using a private, secured workstation.
4. Click **"Log In"**.
5. The system performs secure hash verification and immediately redirects you to your role-specific home environment:
   - **Students** are routed to the **Student Dashboard** (`/dashboard`).
   - **Staff Signatories** are routed to the **Staff Pending Requests Queue** (`/staff/pending-requests`).
   - **College President** is routed to the **President Final Approvals Portal** (`/president/final-approvals`).
   - **Administrators / OSAS** are routed to the **Admin Analytics Dashboard** (`/admin/dashboard`).

### 3.5 Password Recovery & Account Security
- If you forget your password, click **"Forgot your password?"** on the login view.
- Enter your registered email address and click **"Email Password Reset Link"**.
- Follow the instructions in the email link to establish a new password.
- Always remember to click **"Log Out"** located in the top-right profile navigation menu prior to leaving a shared workstation.

---

# Part 2: Student User Manual

### 4.1 Navigating the Student Dashboard
The Student Dashboard is dynamically customized to match your enrolled program's color identity (e.g., Emerald for Agriculture, Blue for Information System, Red for Criminology).

```
+-----------------------------------------------------------------------------+
| [TPC Logo]  Student Clearance Dashboard          (Active: 1st Sem 2026-2027)|
+-----------------------------------------------------------------------------+
| Welcome back, JUAN DELA CRUZ!                   Course: BSIS  •  Year: 4th  |
| Overall Status: IN PROGRESS [==========>              ] 45% Cleared         |
+-----------------------------------------------------------------------------+
| [ Submit Initial Request ]  or  [ Request More Offices ]                    |
+-----------------------------------------------------------------------------+
| Clearance Office Items:                                                     |
|  1. Guidance Office          [ APPROVED ]     Cleared on Sep 12, 2:30 PM    |
|  2. Library                  [ REJECTED ]     "Overdue book: Java Basics"   |
|                                               [ MARK AS COMPLIED ]          |
|  3. Security & Safety        [ PENDING  ]     Awaiting staff action         |
|  4. Program Head (Locked)    [ LOCKED   ]     Requires: Library             |
+-----------------------------------------------------------------------------+
```

Key elements visible on your screen:
- **Active Term Banner**: Indicates the current academic semester and school year configured by OSAS.
- **Progress Gauge**: Visual percentage meter displaying cleared versus remaining signatory obligations.
- **Action Buttons**: Direct triggers to submit initial clearances, request newly unlocked offices, or view final receipts.
- **Offices Card Grid / List**: Comprehensive display of all offices assigned to your course, their prerequisite dependencies, current status badges, and signatory remarks.

### 4.2 Step 1: Submitting an Initial Clearance Request
When entering a new academic clearance cycle, no offices are requested initially.

1. On your dashboard, click the prominent **"Submit Clearance Request"** button.
2. An interactive selection modal opens, listing all regular offices assigned to your curriculum.
3. Offices that have **no unmet prerequisites** are selectable with an active checkbox.
   *(Offices requiring prerequisites to be cleared first are marked "Locked by Prerequisites" and remain disabled).*
4. Select all available offices you wish to clear or click **"Select All Available"**.
5. Click **"Submit Request"**.
6. The selected offices transition from `Not Requested` to `Pending`. Designated staff members receive immediate in-app notifications.

> [!NOTE]
> **Clearance Period Activation**: Clearance submissions are only enabled when the clearance period has been started by the OSAS Administrator. If clearance is currently stopped or closed, the dashboard displays a *"Clearance Period Inactive"* notice with locked submission buttons. Already-cleared students can still access and download their receipts anytime.

### 4.3 Step 2: Understanding Sequential Prerequisites
The clearance system enforces sequential administrative rules to ensure institutional accountability.

#### Example Prerequisite Hierarchy:
- **Guidance Office** &rarr; *No prerequisites* (Available immediately).
- **Library** &rarr; *No prerequisites* (Available immediately).
- **Program Head** &rarr; *Requires: Library & Guidance Office*.
- **Office of Student Affairs and Services (OSAS)** &rarr; *Requires: Program Head*.
- **College President** &rarr; *Requires: ALL 13 regular offices to be fully cleared*.

> [!IMPORTANT]
> You cannot request approval from an office until every one of its configured prerequisite offices has achieved **Approved** status.

### 4.4 Step 3: Requesting Newly Unlocked Offices
As staff signatories approve your pending requests, dependent offices will automatically unlock!

1. Regularly check your dashboard (the interface automatically updates every 5 seconds).
2. When a prerequisite is cleared, formerly locked offices display an **Unlocked** status.
3. Click the **"Request More Offices"** button.
4. Check the boxes for the newly unlocked offices.
5. Click **"Submit Request"**. These offices now transition into the pending queues for their respective staff signatories.

### 4.5 Step 4: Tracking Real-Time Status & Notifications
Every clearance item reflects one of four statuses:

| Status Badge | Meaning | Next Action Required |
| :--- | :--- | :--- |
| `Not Requested` | Office is available or locked; request has not been sent. | Select and click "Submit Request" once unlocked. |
| `Pending` | Request has been successfully delivered to the office queue. | Wait for office staff evaluation. |
| `Approved` | Office signatory has evaluated and cleared your record. | None; progresses you towards unlocking subsequent offices. |
| `Rejected` | Office staff detected an unresolved deficiency. | Read remarks, settle obligation, and Mark as Complied. |

When staff act on your request, an in-app notification appears on your notification bell icon in the top header bar.

### 4.6 Step 5: Handling Deficiencies & Rejections (Compliance Workflow)
If an office rejects your clearance request:
1. The office card on your dashboard will turn red and display a **Rejected** status badge.
2. Review the **Signatory Remarks** displayed inside the card (e.g., *"Unreturned laboratory apparatus #14"*, *"Pending SSG sports fee balance of P150"*).
3. Fulfill the requirement physically or digitally with the specified department.
4. Once you have settled the obligation, locate the rejected card on your dashboard and click the **"Mark as Complied"** button.
5. Confirm the action in the prompt. The item status immediately returns to **Pending**, notifying the staff signatory that you have fulfilled the requirements and are ready for re-review.

### 4.7 Step 6: Requesting College President Final Clearance
The **Office of the College President** acts as the supreme institutional signatory.

1. Continue clearing departmental offices until **100% of all regular offices (13 out of 13) are marked "Approved"**.
2. Once the final regular office is approved, the **Office of the College President** unlocks.
3. If not requested automatically, click the **"Request Final Approval"** button.
4. Your clearance request is now transferred directly to the College President's executive queue.

### 4.8 Step 7: Viewing & Printing Official Clearance Receipt
Once the College President grants final approval:
- Your overall clearance status updates to **CLEARED**.
- A celebratory banner appears on your dashboard, accompanied by an active **"View Clearance Receipt"** button.
- Click **"View Clearance Receipt"** to open the official web receipt (`/clearance-receipts/{id}`).
- The web receipt features:
  * Official Talibon Polytechnic College header and insignia.
  * Student identification: Full Name, Student ID, Academic Program, and Year Level.
  * Active Academic Term and School Year.
  * Generated Official Receipt Number (e.g., `TPC-CLR-2026-000042`).
  * Itemized breakdown of all 14 offices with approving officer names and exact timestamps.
  * High-resolution, dynamic **Anti-Fraud QR Code**.
  * Printable via your browser's Print dialog (**Ctrl + P** or clicking **"Print Receipt"**).

### 4.9 Step 8: Downloading the Official PDF Certificate
For enrollment, graduation, or scholarship submissions requiring a standalone digital file:
1. On the Clearance Receipt view, click the **"Download PDF"** button.
2. The server compiles a PDF document via DomPDF.
3. The downloaded file is officially titled and stamped with the exact institutional layout, complete with the embedded QR code and verification token.

---

# Part 3: Office Staff & Department Signatory Manual

### 5.1 Staff Dashboard & Pending Requests Queue
Staff members access the system via the dedicated **Staff Approvals Portal** (`/staff/pending-requests`).

Upon login, staff members only see clearance requests relevant to their assigned office (e.g., Library Staff only sees requests directed to the Library).

```
+-----------------------------------------------------------------------------+
| [TPC Logo]  Staff Portal: LIBRARY                       (Active Term: 1st Sem)
+-----------------------------------------------------------------------------+
| Summary: [ 12 Pending ]    [ 148 Approved ]    [ 3 Rejected ]               |
+-----------------------------------------------------------------------------+
| Search: [ Filter by Student ID / Name... ]  Course: [ All ]  Year: [ All ]  |
|                                                  [ APPROVE ALL PENDING (12)]|
+-----------------------------------------------------------------------------+
| Pending Clearance Queue:                                                    |
|                                                                             |
| • DELA CRUZ, JUAN (2023-0012) - BSIS 4th Year                               |
|   Submitted: Sep 16, 2026 10:15 AM               [ APPROVE ]   [ REJECT ]   |
|                                                                             |
| • SANTOS, MARIA (2023-0045) - BECED 2nd Year                               |
|   Submitted: Sep 16, 2026 10:30 AM               [ APPROVE ]   [ REJECT ]   |
+-----------------------------------------------------------------------------+
```

### 5.2 Filtering, Searching, and Sorting Students
To quickly isolate specific students:
- **Status Tabs**: Toggle between **Pending**, **Approved**, and **Rejected** queues, or select **All** for full history.
- **Search Bar**: Type any portion of the student's name or Student ID number. Results filter instantaneously.
- **Course / Program Dropdown**: Filter students by degree program (e.g., isolate all `BSCRIM` students).
- **Year Level Dropdown**: Filter by year standing (1st, 2nd, 3rd, or 4th Year).

### 5.3 Approving an Individual Clearance Request
1. Locate the student in the **Pending** queue.
2. Cross-reference their institutional obligations (e.g., check your physical logbook or department database for missing materials or unpaid fees).
3. If the student has satisfied all departmental obligations, click the green **"Approve"** button.
4. A confirmation modal will appear: *"Are you sure you want to approve clearance for [Student Name]?"*
5. Click **"Confirm Approval"**.
6. The student's record immediately transitions to **Approved**, the approving officer's user ID and timestamp are recorded, and the student receives a real-time notification.

### 5.4 Bulk Clearance Approvals ("Approve All")
During peak clearance periods where an entire batch of students has no holds:
1. Navigate to the **Pending** tab.
2. Review the pending list.
3. Click the **"Approve All"** button located at the top-right of the table.
4. A security modal prompts: *"Are you sure you want to approve all [X] pending clearance requests for your office?"*
5. Click **"Yes, Approve All"**.
6. The system executes a batch database update, approving all records simultaneously and notifying every affected student.

### 5.5 Rejecting Clearances with Mandatory Deficiency Remarks
If a student has unfulfilled obligations:
1. Click the red **"Reject"** button on the student's pending card.
2. A modal titled **"Reject Clearance Request"** appears.
3. Enter explicit, clear instructions in the **Remarks** text area (e.g., *"Return textbook 'Operating Systems 8th Edition' borrowed on Aug 15"* or *"Settle laboratory breakage fee of P250 at Cashier"*).
4. Click **"Confirm Rejection"**.
5. The request moves to the **Rejected** tab. The student is immediately alerted with your exact remarks so they can take corrective action.

### 5.6 Marking as Complied on Behalf of Students
When a student visits your office and settles their deficiency in person:
1. Switch to the **Rejected** tab.
2. Locate the student and click **"Mark as Complied"**.
3. The system clears the rejection state and shifts the record back to **Pending** status.
4. You can then immediately click **"Approve"** to finalize their clearance.

---

# Part 4: College President (Final Approver) Manual

### 6.1 Executive Final Approvals Portal
The College President or authorized executive officer accesses the system via `/president/final-approvals`.

This portal is reserved strictly for high-level institutional authorization.

```
+-----------------------------------------------------------------------------+
| [TPC Logo]  Office of the College President - Final Clearance Approvals     |
+-----------------------------------------------------------------------------+
| Students Ready for Final Approval: [ 24 Candidates ]                        |
|                                           [ AUTO APPROVE ALL READY (24) ]   |
+-----------------------------------------------------------------------------+
| Filter: [ All Statuses ] [ Course ] [ Year ] | Search: [ Student Name/ID ]  |
+-----------------------------------------------------------------------------+
| • ALVAREZ, MARVIN (2022-0089) - BSIS 4th Year                               |
|   Departmental Signatures: 13 / 13 Cleared (100%)                           |
|   [ View Department Audit ]        [ APPROVE FINAL ]        [ REJECT ]      |
+-----------------------------------------------------------------------------+
```

### 6.2 Ready-for-Final-Approval Queue Logic
To ensure total academic integrity, the system applies strict database filtering:
- A student **ONLY** appears in the President's "Ready" queue if **every single one of the 13 regular offices is in 'Approved' status**.
- If even one department has rejected or not yet acted on the student's request, the record cannot be finalized by the President.

### 6.3 Inspecting Departmental Audit Trails
Before approving, the President can inspect the student's full institutional record:
1. Click the student's card to expand the **Clearance Audit Drawer**.
2. Review the chronological list of all 13 offices.
3. Verify the name of each staff member who signed off and the exact date and time of approval.

### 6.4 Granting Final Approval (Individual & Bulk)
#### Individual Final Approval:
1. Click the **"Approve"** button on the student's card.
2. The system executes the finalization routine:
   - Updates the approval record to `Approved`.
   - Generates the official Receipt Number.
   - Generates the cryptographic 32-character Verification Code.
   - Sets overall clearance status to `Cleared`.
   - Records the official `cleared_at` timestamp.
   - Dispatches a real-time completion alert to the student.

#### Bulk Final Approval ("Approve All"):
1. Click **"Auto Approve All Ready"** at the top of the portal.
2. Confirm the prompt: *"Approve final clearance for all [X] candidate students?"*
3. The system batch-processes every ready candidate, issuing official clearance receipts for all of them.

### 6.5 Generating Official Receipt Numbers & Cryptographic Verification Tokens
Every cleared clearance request automatically receives:
- **Receipt Number**: Formatted as `TPC-CLR-[YEAR]-[6-DIGIT ID]` (e.g., `TPC-CLR-2026-000105`).
- **Verification Hash**: A high-entropy 32-character uppercase token (e.g., `A9F8E2D7C4B105638291FEEA7340BC91`).
- **QR Code Payload**: Encodes the public verification URL linking directly to the institutional verification endpoint.

### 6.6 Handling Presidential Rejections & Compliance Holds
In rare cases where an executive or disciplinary hold exists at the presidential level:
1. Click **"Reject"**.
2. Enter the executive reason in the remarks field.
3. The student is notified of the executive hold. Once cleared, the President can click **"Mark as Complied"** to restore the request to the pending approval queue.

---

# Part 5: System Administrator & OSAS Director Manual

### 7.1 Administrative Analytics Dashboard
The Administrator / OSAS Director acts as the system manager via `/admin/dashboard`.

The dashboard presents real-time institutional metrics:
- **Total Students Registered**
- **Total Staff Signatories Active**
- **Active Academic Courses & Departments**
- **Total Clearance Requests (Current Term)**
- **Pending Approvals Count**
- **Approved Clearances Count**
- **Rejected Clearances Count**
- **Recent Clearance Activity Feed**

### 7.2 User Management & Staff Provisioning
Administrators manage all user accounts via **User Management** (`/admin/users`).

```
+-----------------------------------------------------------------------------+
| User Management                          [ + Create New Staff Account ]     |
+-----------------------------------------------------------------------------+
| Name            Student ID / Email     Role       Office / Course   Status  |
|-----------------------------------------------------------------------------|
| Maria Santos    LIB001                 Staff      Library           ACTIVE  |
| Juan Dela Cruz  2023-0012              Student    BSIS (4th Year)   ACTIVE  |
| Dr. E. Ramos    PRES001                President  College President ACTIVE  |
+-----------------------------------------------------------------------------+
```

#### Creating a New Staff Account:
1. Click **"+ Create New Staff Account"** (`/admin/users/create`).
2. Input the Staff Member's **Full Name**, official **Institutional Email**, and unique **Employee / Staff ID**.
3. Select their assigned **Clearance Office** from the dropdown.
4. Set an initial password and confirm it.
5. Click **"Create Staff Account"**.

#### Editing Users & Toggling Account Status:
- Click **"Edit"** on any user row to modify their name, email, assigned office/course, or reset their password.
- Click **"Deactivate"** to temporarily freeze access for staff on leave or inactive students. Deactivated users are immediately blocked from logging in. Click **"Activate"** to restore access.

### 7.3 Course Modules & Signatory Office Configuration
Different academic degree programs may require distinct combinations of signatory offices (e.g., Criminology students requiring specific tactical equipment clearance).

Navigate to **Course Modules** (`/admin/course-modules`):
1. Select an academic degree program (e.g., `BSIS`).
2. The screen displays all 13 regular offices with checkboxes.
3. Check the offices that students of this program are required to clear.
4. Click **"Save Office Assignments"**.
5. All future clearance requests submitted by students in that program will dynamically enforce this tailored office list.

### 7.4 Office Prerequisites Configuration
The clearance sequence is configured via **Office Prerequisites** (`/admin/office-prerequisites`).

```
+-----------------------------------------------------------------------------+
| Office Prerequisites Configuration                                          |
+-----------------------------------------------------------------------------+
| Office Name               Prerequisites Required Before Request Can Be Made |
|-----------------------------------------------------------------------------|
| Guidance Office           [ None - Available at start ]                     |
| Library                   [ None - Available at start ]                     |
| Program Head              [x] Library   [x] Guidance Office                 |
| OSAS                      [x] Program Head                                  |
+-----------------------------------------------------------------------------+
```

1. Locate the office you wish to constrain (e.g., *Program Head*).
2. Check the offices that must be cleared prior to this office (e.g., select *Library* and *Guidance Office*).
3. Click **"Update Prerequisites"**.
4. The system updates its dependency graph. Students are now prevented from requesting the Program Head until both prerequisite offices have signed off.

### 5.5 Academic Term Settings & Clearance Cycle Cycling
At the start of every new semester or school year, the Administrator cycles the clearance term via **Settings** (`/admin/settings`).

#### 5.5.1 Clearance Period Start / Stop Controls
Administrators can start or stop the clearance period on-demand to enforce official campus clearance schedules:
1. Navigate to **System Settings** (`/admin/settings`).
2. Locate the **Clearance Period Status** card at the top:
   - **When Active / Open**: Students can submit initial clearance requests and request newly unlocked departments. Click **"Stop Clearance Period"** when clearance week ends to lock submissions.
   - **When Stopped / Closed**: Student submission controls are safely locked. Students who have already been cleared can still view, print, and download their certificates. Click **"Start Clearance Period"** to open submissions for the term.
3. **Notice to Students**: Enter custom instructions or announcements (e.g., *"Clearance for 1st Sem 2026-2027 opens Oct 15"*) in the notice area and click **"Update Notice"**. This message is instantly displayed on every student's dashboard.

#### 5.5.2 Cycling Academic Terms
1. Select the new **Active Semester**:
   - `1st Semester`
   - `2nd Semester`
   - `Summer`
2. Enter the **Active School Year** (e.g., `2026-2027`).
3. Type `RESET CLEARANCES` and click **"Change Term"**.

> [!CAUTION]
> **Term Cycling Behavior**: Updating the active term resets the clearance workspace for the new semester. Students will be able to submit fresh clearance requests for the new term. All historical requests from previous semesters remain permanently preserved in the database for auditing and historical reporting.

### 7.6 Clearance Requests Master Audit View
Navigate to **Clearance Requests** (`/admin/clearance-requests`) for an institutional bird's-eye view of all student submissions across all semesters.
- View real-time progress bars for every student.
- Click **"View Details"** (`/admin/clearance-requests/{id}`) to inspect complete approval histories, timestamps, and staff remarks.

### 7.7 Official Clearance Reports, Analytics & Exports
Located at `/admin/reports`, this module provides administrative intelligence and exportable clearance sheets.

#### Filtering and Summaries:
- Filter reports by **Semester**, **School Year**, **Degree Program / Course**, and **Status** (*Cleared*, *Pending*, or *Needs Attention*).
- View instant summary cards: Total Requests, Total Cleared, Total Pending, and Total with Deficiencies.

#### Exporting to CSV:
1. Apply your desired filters.
2. Click **"Export CSV"** (`/admin/reports/export-csv`).
3. The browser downloads a `.csv` spreadsheet containing: Student Name, Student ID, Course, Year Level, Semester, School Year, Progress Ratio, Status, and Cleared Date.

#### Generating the Official Printable Report:
1. Click **"Print Report"** (`/admin/reports/print`).
2. A formal institutional report layout renders with official TPC headers, filter metadata, summary tally tables, and an alphabetical master list of students.
3. Use the browser's print dialog to print hard copies or save as a presentation-grade PDF.

---

# Part 6: Public Verification, Troubleshooting & Support

### 6.1 Public Verification Portal Overview
Any third party possessing a student's clearance receipt can authenticate its legitimacy without needing a system login.

Verification URL format:
```
https://[domain-name]/verify-clearance/{verificationCode}
```

### 8.2 QR Code Scanning & Direct Verification
1. Open any standard smartphone camera or QR code scanner application.
2. Point the camera at the QR code printed on the student's physical or digital clearance receipt.
3. Tap the detected URL notification.
4. The browser securely connects to the **TPC Public Clearance Verification Portal**.

### 8.3 Interpreting Verification States (Valid vs. Invalid)

#### Valid & Cleared Record (Green Banner):
If the clearance certificate is authentic and cleared by the College President, the portal displays:
- **Status**: `VALID AND FULLY CLEARED`
- **Official Receipt Number**: e.g., `TPC-CLR-2026-000042`
- **Student Full Name**: Legal student name matching institutional records.
- **Student ID**: Official student number.
- **Degree Program & Major**: Complete course title.
- **Academic Term**: Semester and School Year cleared.
- **Presidential Sign-Off**: Name of College President and timestamp of approval.

#### Invalid or Incomplete Record (Red / Amber Banner):
If an invalid verification code is entered or the record is altered:
- The portal warns: *"No clearance record was found for this verification code"* or *"This clearance record exists but is not fully cleared."*
- This mechanism guarantees complete immunity against forged signatures or counterfeit paper clearance slips.

### 6.4 Common Student Questions & Solutions

#### Q1: Why does my dashboard say "Clearance Period Inactive" and the submit button is locked?
**Answer**: The Office of Student Affairs and Services (OSAS) has not opened the clearance period yet for this semester (or the deadline has passed). Once OSAS activates the clearance period, your dashboard will automatically unlock without needing a page refresh.

#### Q2: Why are certain offices disabled when I try to submit my clearance request?
**Answer**: These offices have unmet prerequisites. Check the office card on your dashboard to see which prerequisite offices must be cleared first. Once those prerequisite offices approve your request, the locked offices will automatically become selectable.

#### Q3: What should I do if my clearance request is rejected?
**Answer**: Review the remarks displayed on the rejected office card. Settle the obligation with that department (e.g., return books, pay fees), then click **"Mark as Complied"** on your dashboard. This notifies the office to review your request again.

#### Q4: Why can't I request the College President's final approval?
**Answer**: The College President's office only unlocks after all 13 regular offices have achieved **Approved** status. Ensure there are no pending or rejected departmental items remaining.

#### Q5: How do I get my official clearance receipt after being cleared?
**Answer**: Once the College President approves your request, click **"View Clearance Receipt"** on your dashboard. From there, you can print the receipt or click **"Download PDF"** to save an official copy.

---

### 6.5 Common Staff & Approver Questions

#### Q1: Why don't I see students from other departments in my queue?
**Answer**: As an office staff member, your queue only displays clearance requests specifically submitted to your assigned office.

#### Q2: Can I reverse an accidental approval?
**Answer**: Once an approval is granted, it locks into the audit trail. If an approval was made in error, contact the OSAS Administrator immediately to make the necessary administrative adjustments.

#### Q3: When should I use the "Approve All" button?
**Answer**: Use "Approve All" during peak clearance periods when you have verified that all students currently pending in your queue have no holds or deficiencies in your department.

---

### 6.6 Common Administrative Questions

#### Q1: What happens to existing clearance records when I update the active semester?
**Answer**: Existing clearance records are safely preserved in the database. Updating the active semester initializes a fresh clearance cycle for the new term while keeping all past records available in reports and audit logs.

#### Q2: A student registered with the wrong course. How can I fix it?
**Answer**: Go to **User Management** (`/admin/users`), find the student, click **"Edit"**, select their correct course from the dropdown, and save the changes.

---

### 6.7 Technical Support & Escalation Channels

For assistance with account lockouts, data corrections, or technical inquiries:
- **Office of Student Affairs and Services (OSAS)**
  * Location: Ground Floor, Administration Building, TPC Main Campus, San Isidro, Talibon, Bohol
  * Email: `osas@tpc.edu.ph` / `admin@university.edu`
- **Management Information System / ICT Support**
  * Email: `ictsupport@tpc.edu.ph`


---

# APPENDIX K: DATABASE SCHEMA

### Table K.1. Users Table Data Dictionary (users)

| Field Name | Data Type | Null | Key / Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| **id** | BIGINT(20) UNSIGNED | NO | PRIMARY KEY, AUTO_INC | Unique surrogate identifier for each institutional user account. |
| **student_id** | VARCHAR(255) | YES | UNIQUE KEY | Official institutional student ID number (e.g., TPC-2024-0012). Null for non-student roles. |
| **name** | VARCHAR(255) | NO | None | Full legal name of the user or account display name. |
| **email** | VARCHAR(255) | YES | UNIQUE KEY | Official institutional or personal email address used for system login and alerts. |
| **course_id** | BIGINT(20) UNSIGNED | YES | FOREIGN KEY -> courses(id) | Foreign key referencing the student's enrolled academic program. Null for administrative staff. |
| **office_id** | BIGINT(20) UNSIGNED | YES | FOREIGN KEY -> offices(id) | Foreign key referencing the staff member's assigned clearance office. Null for students. |
| **role** | ENUM('student', 'staff', 'admin', 'president') | NO | DEFAULT 'student' | Role-Based Access Control (RBAC) role defining system privileges and navigation. |
| **is_active** | TINYINT(1) | NO | DEFAULT 1 | Boolean status flag indicating account activation (1 = Active, 0 = Deactivated). |
| **deactivated_at** | TIMESTAMP | YES | None | Timestamp recording when the user account was deactivated by the system administrator. |
| **email_verified_at** | TIMESTAMP | YES | None | Timestamp indicating when the user verified their email address. |
| **password** | VARCHAR(255) | NO | None | Bcrypt-hashed password string for secure authentication. |
| **remember_token** | VARCHAR(100) | YES | None | Cryptographic token for persistent browser session authentication. |
| **created_at** | TIMESTAMP | YES | None | Record creation audit timestamp managed by Eloquent ORM. |
| **updated_at** | TIMESTAMP | YES | None | Record modification audit timestamp managed by Eloquent ORM. |

---

### Table K.2. Courses Table Data Dictionary (courses)

| Field Name | Data Type | Null | Key / Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| **id** | BIGINT(20) UNSIGNED | NO | PRIMARY KEY, AUTO_INC | Unique identifier for the academic degree program. |
| **name** | VARCHAR(255) | NO | None | Official title of the academic program (e.g., Bachelor of Science in Information Systems). |
| **code** | VARCHAR(255) | NO | UNIQUE KEY | Standard institutional program code abbreviation (e.g., BSIS, CRIMS, BEED). |
| **created_at** | TIMESTAMP | YES | None | Record creation timestamp. |
| **updated_at** | TIMESTAMP | YES | None | Record modification timestamp. |

---

### Table K.3. Offices Table Data Dictionary (offices)

| Field Name | Data Type | Null | Key / Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| **id** | BIGINT(20) UNSIGNED | NO | PRIMARY KEY, AUTO_INC | Unique identifier for the institutional clearance department. |
| **name** | VARCHAR(255) | NO | None | Official departmental office name (e.g., Library, Cashier, Dean, Registrar, Guidance, Student Affairs). |
| **group** | VARCHAR(255) | YES | None | Administrative grouping or category designation for the office. |
| **sort_order** | INT(10) UNSIGNED | NO | DEFAULT 0 | Numerical priority index controlling display sequencing and topological queue order. |
| **is_final_approver** | TINYINT(1) | NO | DEFAULT 0 | Boolean flag designating the office as the executive final gatekeeper (1 = College President, 0 = Standard Department). |
| **created_at** | TIMESTAMP | YES | None | Record creation timestamp. |
| **updated_at** | TIMESTAMP | YES | None | Record modification timestamp. |

---

### Table K.4. Course-Office Junction Table Data Dictionary (course_office)

| Field Name | Data Type | Null | Key / Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| **id** | BIGINT(20) UNSIGNED | NO | PRIMARY KEY, AUTO_INC | Unique surrogate identifier for the curriculum-office mapping entry. |
| **course_id** | BIGINT(20) UNSIGNED | NO | FK -> courses(id), UNIQUE(1) | Foreign key referencing the academic course. Part of composite unique key (course_id, office_id). |
| **office_id** | BIGINT(20) UNSIGNED | NO | FK -> offices(id), UNIQUE(2) | Foreign key referencing the mandatory clearance office for the linked course. Cascades on delete. |
| **created_at** | TIMESTAMP | YES | None | Record creation timestamp. |
| **updated_at** | TIMESTAMP | YES | None | Record modification timestamp. |

---

### Table K.5. Office Prerequisites Junction Table Data Dictionary (office_prerequisites)

| Field Name | Data Type | Null | Key / Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| **office_id** | BIGINT(20) UNSIGNED | NO | PK(1), FK -> offices(id) | Foreign key referencing the target clearance office requiring a prerequisite. Cascades on delete. |
| **prerequisite_office_id** | BIGINT(20) UNSIGNED | NO | PK(2), FK -> offices(id) | Foreign key referencing the prerequisite office that must be cleared prior to the target office. |

---

### Table K.6. Clearance Requests Table Data Dictionary (clearance_requests)

| Field Name | Data Type | Null | Key / Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| **id** | BIGINT(20) UNSIGNED | NO | PRIMARY KEY, AUTO_INC | Unique surrogate identifier for the student clearance application filing. |
| **user_id** | BIGINT(20) UNSIGNED | NO | FK -> users(id), UNIQUE(1) | Foreign key referencing the applying student in the users table. Cascades on delete. |
| **semester** | VARCHAR(255) | NO | INDEX(1), UNIQUE(2) | Academic semester term of application (e.g., '1st Semester', '2nd Semester', 'Summer'). |
| **school_year** | VARCHAR(255) | NO | INDEX(2), UNIQUE(3) | Academic school year of application (e.g., '2026-2027'). Prevents duplicate semester filings. |
| **status** | ENUM('pending', 'cleared') | NO | DEFAULT 'pending' | Overall master state of the clearance filing. Transitions to 'cleared' once all obligations are fulfilled. |
| **submitted_at** | TIMESTAMP | YES | None | Exact date and time the student formally submitted the online clearance application. |
| **cleared_at** | TIMESTAMP | YES | None | Exact date and time when final executive approval was recorded, granting overall clearance. |
| **receipt_number** | VARCHAR(255) | YES | UNIQUE KEY | Official alphanumeric receipt serial number generated automatically upon full clearance completion. |
| **verification_code** | VARCHAR(255) | YES | UNIQUE KEY | Cryptographic alphanumeric verification token embedded into the scannable QR certificate code. |
| **created_at** | TIMESTAMP | YES | None | Record creation timestamp. |
| **updated_at** | TIMESTAMP | YES | None | Record modification timestamp. |

---

### Table K.7. Clearance Approvals Table Data Dictionary (clearance_approvals)

| Field Name | Data Type | Null | Key / Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| **id** | BIGINT(20) UNSIGNED | NO | PRIMARY KEY, AUTO_INC | Unique surrogate identifier for the departmental clearance evaluation line item. |
| **clearance_request_id** | BIGINT(20) UNSIGNED | NO | FK -> clearance_requests(id), UNIQUE(1) | Foreign key referencing the parent clearance request. Cascades on delete. |
| **office_id** | BIGINT(20) UNSIGNED | NO | FK -> offices(id), UNIQUE(2), INDEX(1) | Foreign key referencing the evaluating department. Scopes staff pending queues. |
| **approved_by** | BIGINT(20) UNSIGNED | YES | FOREIGN KEY -> users(id) | Foreign key referencing the authenticated staff member who acted on the obligation. Sets NULL on delete. |
| **status** | ENUM('not_requested', 'pending', 'approved', 'rejected') | NO | DEFAULT 'not_requested', INDEX(2) | Granular departmental evaluation state indicating obligation compliance status. |
| **remarks** | TEXT | YES | None | Explicit deficiency descriptions, monetary obligations, or settlement instructions provided upon rejection. |
| **acted_at** | TIMESTAMP | YES | None | Exact timestamp when the staff signatory approved or rejected the departmental requirement. |
| **created_at** | TIMESTAMP | YES | None | Record creation timestamp. |
| **updated_at** | TIMESTAMP | YES | None | Record modification timestamp. |

---

### Table K.8. Notifications Table Data Dictionary (notifications)

| Field Name | Data Type | Null | Key / Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| **id** | BIGINT(20) UNSIGNED | NO | PRIMARY KEY, AUTO_INC | Unique surrogate identifier for the in-app notification record. |
| **user_id** | BIGINT(20) UNSIGNED | NO | FOREIGN KEY -> users(id) | Foreign key referencing the recipient user account. Cascades on user deletion. |
| **title** | VARCHAR(255) | NO | None | Brief summary headline of the alert (e.g., 'Clearance request rejected', 'Clearance marked as complied'). |
| **message** | TEXT | NO | None | Detailed notification body containing specific departmental feedback and cited deficiency remarks. |
| **link** | VARCHAR(255) | YES | None | Internal application route directing the recipient to relevant dashboard views (e.g., '/dashboard'). |
| **read_at** | TIMESTAMP | YES | None | Timestamp recording when the user opened or read the notification (null indicates unread). |
| **created_at** | TIMESTAMP | YES | None | Record creation timestamp. |
| **updated_at** | TIMESTAMP | YES | None | Record modification timestamp. |

---

### Table K.9. Application Settings Table Data Dictionary (app_settings)

| Field Name | Data Type | Null | Key / Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| **id** | BIGINT(20) UNSIGNED | NO | PRIMARY KEY, AUTO_INC | Unique surrogate identifier for the system configuration setting. |
| **key** | VARCHAR(255) | NO | UNIQUE KEY | Unique configuration key identifier (e.g., 'active_semester', 'active_school_year'). |
| **value** | TEXT | YES | None | Global setting value stored as text and cached via Laravel Cache facade for fast runtime retrieval. |
| **created_at** | TIMESTAMP | YES | None | Record creation timestamp. |
| **updated_at** | TIMESTAMP | YES | None | Record modification timestamp. |
