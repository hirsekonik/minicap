# TPC Web-Based Student Clearance System: Master Documentation

---

# PART 1: Frequently Asked Questions (FAQ)

## 1. General Questions

**Q: What is the Web-Based Student Clearance System?**
A: The Web-Based Student Clearance System is an automated platform designed to help graduating students and transferring students securely process their clearance requirements online without the need for physical signatures from all offices.

**Q: Who is required to get a clearance?**
A: All graduating students, transferring students, and students taking a leave of absence (LOA) must secure a clearance before they can request their Transcript of Records (TOR) or Honorable Dismissal.

**Q: Can I process my clearance if I have remaining balance?**
A: No. All financial obligations must be settled at the Cashier's Office before your clearance can progress.

## 2. Process and Timeline

**Q: How long does the clearance process take?**
A: Once a student submits a clearance request through the portal, it typically takes 3 to 5 working days for all departments to review and approve the request, provided the student has no pending accountabilities.

**Q: How do I know if I have a pending accountability?**
A: You can log into your Student Portal and navigate to the "Clearance Status" dashboard. Any pending accountability will be flagged in red with remarks from the respective office (e.g., "Unreturned Book" from the Library).

**Q: What happens if an office rejects my clearance?**
A: If your clearance is rejected, you must read the remarks provided by the Office Staff, physically go to that specific office to resolve the issue (e.g., returning a borrowed item), and then click the "Re-evaluate" button on the portal.

---

# PART 2: Technical Workflow & Architecture

## 1. System Entities
The Web-Based Student Clearance System is built around several core entities:
* **Users:** Includes Students (who initiate requests), Office Staff (who approve/reject requests), and Administrators (who manage settings).
* **Courses/Programs:** Represents the academic program the student belongs to, which determines their specific clearance routing.
* **Offices (Signatories):** The specific departments required to sign off on a clearance. The system groups these into two categories:
  * **Student Services:** Guidance Office, Medical-Dental Clinic, Library, Security and Safety Office, Equipment and Facilities, Supreme Student Government (SSG), Registrar, PE/Sports, Canteen.
  * **Offices and Administration:** Program Head, Office of Student Affairs and Services (OSAS), Office of the Vice President for Academic Affairs, Office of the Vice President for Administration, Office of the College President.
* **Clearance Requests:** The overarching application submitted by a student.
* **Clearance Approvals:** The individual, department-level approval records linked to a specific Clearance Request.

## 2. Request Initiation Phase
1. A Student logs into the portal and clicks "Request Clearance".
2. The system generates a new **Clearance Request** record with a status of "Pending".
3. The system automatically creates multiple **Clearance Approval** records—one for every **Office** in the sequence.
4. Notifications are pushed to the dashboards of the respective Office Staff.

## 3. Approval Routing and Logic
* Office Staff can view all pending **Clearance Approvals** assigned to their specific Office.
* Staff can change the status to "Approved" or "Rejected". 
* **Rejections:** If an Office rejects a clearance, they must provide mandatory remarks (e.g., "Unpaid laboratory fee"). The student is immediately notified. The overarching **Clearance Request** remains "Pending" but is flagged with an issue.
* **Approvals:** When an Office approves, their specific **Clearance Approval** record is locked.

## 4. Final Completion
1. The **Office of the College President** is designated as the sole `is_final_approver` in the system.
2. The overarching **Clearance Request** will only change from "Pending" to "Completed" when *every single* associated **Clearance Approval** record is marked as "Approved", culminating with the College President.
3. Once Completed, the student can download and print their officially generated Clearance Receipt containing a unique reference number.

---

# PART 3: Departmental Accountability Rules

## A. Library Accountability Rules
* All borrowed library materials must be returned on or before the last day of final examinations.
* The Librarian will reject the clearance and add a remark if there are overdue fines or unreturned books.
* Lost books must be replaced with the exact title/edition or paid for at current market value plus a 20% processing fee.

## B. Supreme Student Government (SSG) Rules
* Officers of the Supreme Student Government (SSG) must submit all financial liquidation reports and turnover documents to the SSG Adviser before their clearance is approved.

## C. Office of Student Affairs and Services (OSAS) Guidelines
* OSAS verifies if a student has any pending disciplinary cases.
* Graduating students must surrender their official TPC Student ID Card to OSAS upon final exit.
* A student with an ongoing disciplinary case will have their clearance rejected by OSAS until the sanctions (e.g., community service) are completed.

## D. Equipment and Facilities Guidelines
* Any student who has borrowed laboratory equipment, sports gear, or utilized campus facilities must ensure everything is returned in good condition.
* The Equipment and Facilities office will reject a clearance if there are reported breakages or missing items.

## E. Registrar Guidelines
* The Registrar verifies that all grades have been submitted and the student has completed the required number of units for their specific Course.
* Only after the final clearance is completed can a student request their Transcript of Records (TOR) or Honorable Dismissal from the Registrar.

## F. Program Head and Academic Approvals
* The Program Head must certify that the student has completed their thesis/capstone project, submitted all hardbound copies, and fulfilled their academic obligations for the program.

## G. Final Signatory: Office of the College President
* As the designated `is_final_approver` (Sort Order 14), the Office of the College President provides the ultimate sign-off. This office only approves the clearance after all Student Services and other Administration offices have approved their respective sections.
