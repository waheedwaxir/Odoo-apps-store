import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "Odoo 19 Salon & Spa Scheduler & POS Management Suite — Client User Manual")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)
        
        # Footer
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 45, 8.5 * inch - 54, 45)
        
        self.drawString(54, 30, "Confidential & Proprietary — Prepared for Client Deployment")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 30, page_text)
        self.restoreState()

def build_pdf(filename="Salon_Spa_Scheduler_User_Manual.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Palette
    c_primary = colors.HexColor("#1E293B")    # Slate 800
    c_secondary = colors.HexColor("#3B82F6")  # Blue 500
    c_accent = colors.HexColor("#10B981")     # Emerald 500
    c_dark = colors.HexColor("#0F172A")       # Slate 900
    c_text = colors.HexColor("#334155")       # Slate 700
    c_light = colors.HexColor("#F8FAFC")      # Slate 50
    c_border = colors.HexColor("#E2E8F0")     # Slate 200
    c_highlight = colors.HexColor("#FEF3C7")  # Amber 100
    
    # Define Typography
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=c_dark,
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#64748B"),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=c_primary,
        spaceBefore=18,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=c_secondary,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=c_text,
        spaceAfter=8,
        alignment=TA_JUSTIFY
    )
    
    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4,
        alignment=TA_LEFT
    )
    
    callout_style = ParagraphStyle(
        'Callout_Text',
        parent=body_style,
        fontName='Helvetica-Oblique',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1E3A8A"),
        alignment=TA_LEFT,
        spaceAfter=0
    )
    
    story = []
    
    # Title & Header Section
    story.append(Spacer(1, 10))
    story.append(Paragraph("Odoo 19 Salon & Spa Management Suite", title_style))
    story.append(Paragraph("<b>Comprehensive Client User Manual & Technical Guide</b><br/>Version 19.0.1.0 • Complete Workflow & Operational Documentation", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=c_secondary, spaceAfter=15))
    
    # Check if banner exists
    banner_path = "/Users/developer/WS/odoo-19.0/custom-addons/testing-modules/salon_spa_scheduler/static/description/banner.png"
    if os.path.exists(banner_path):
        img = Image(banner_path, width=4.5*inch, height=4.15*inch)
        img.hAlign = 'CENTER'
        story.append(img)
        story.append(Spacer(1, 15))
        
    # Executive Summary
    story.append(Paragraph("1. Executive Summary & Overview", h1_style))
    story.append(Paragraph(
        "The <b>Salon & Spa Scheduler for Odoo 19</b> is a state-of-the-art, end-to-end operational suite engineered specifically for beauty salons, luxury day spas, barbershops, and wellness clinics. It bridges the gap between customer appointment scheduling, multi-step treatment execution, Point of Sale (POS) checkout, beautician tip management, and executive analytical reporting.",
        body_style
    ))
    story.append(Paragraph(
        "By integrating natively into Odoo 19's backend and POS interfaces, this suite eliminates double-bookings, automates customer email confirmations and reminders, accurately calculates beautician commissions and tips, and delivers dynamic visual scheduling.",
        body_style
    ))
    
    # Callout Box
    callout_content = [
        [Paragraph("<b>Key System Highlights:</b><br/>"
                   "• <b>Dynamic Visual Calendar:</b> Real-time scheduler with drag-and-drop resizing and multi-branch color coding.<br/>"
                   "• <b>Adjust Duration Override:</b> Instantly stretch or contract appointment slots and multi-step timings.<br/>"
                   "• <b>Dedicated POS Tip Button:</b> Cashiers select beauticians right at checkout to log tips automatically.<br/>"
                   "• <b>Automated Email Protection:</b> Guaranteed single confirmation email upon booking plus 30-min reminders.<br/>"
                   "• <b>Executive Analytics:</b> Live dashboard tracking revenue, commissions, ratings, and staff tips.", callout_style)]
    ]
    t_callout = Table(callout_content, colWidths=[7.0*inch])
    t_callout.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EFF6FF")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#BFDBFE")),
        ('PADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_callout)
    story.append(Spacer(1, 15))
    
    # Module 1: The Interactive Scheduler
    story.append(Paragraph("2. The Interactive Scheduler & Calendar View", h1_style))
    story.append(Paragraph(
        "The <b>Scheduler</b> tab serves as the primary operational hub for front-desk receptionists and salon managers. It displays a multi-column view categorized by active beauticians, therapists, and stylists.",
        body_style
    ))
    story.append(Paragraph("<b>2.1 Multi-Branch Color Coding</b>", h2_style))
    story.append(Paragraph(
        "To effortlessly manage multi-location operations, every appointment card on the scheduler dynamically inherits the unique color assigned to its branch (`Branch Color`). Receptionists can immediately identify whether a booking belongs to the Downtown branch, Uptown branch, or VIP suite at a single glance without clicking into the record.",
        body_style
    ))
    story.append(Paragraph("<b>2.2 The 'Adjust Duration' Precision Override</b>", h2_style))
    story.append(Paragraph(
        "Normally, selecting a service (such as <i>Hair Coloring</i> or <i>Facial Treatment</i>) calculates an automatic duration based on standard service times. However, clients frequently request extra treatment time or customized adjustments.",
        body_style
    ))
    story.append(Paragraph(
        "• <b>Dynamic Card Resizing:</b> Using the <b>Adjust Duration</b> dropdown (ranging from <i>15 Minutes</i> to <i>4 Hours</i>) instantly recomputes the appointment's exact <code>End Datetime</code>. On the visual Scheduler, the appointment card expands or contracts vertically to occupy the exact visual time block requested.<br/>"
        "• <b>Multi-Step Synchronization:</b> If the appointment consists of sequential steps (e.g., <i>Wash → Cut → Blow Dry</i>), adjusting the total duration automatically scales the final treatment step so that the combined duration of all steps precisely equals the target duration.<br/>"
        "• <b>Interactive Drag-and-Drop:</b> Receptionists can also drag the bottom border of any card directly on the calendar grid. Doing so updates the `Adjust Duration` setting automatically in real time.",
        bullet_style
    ))
    story.append(Spacer(1, 10))
    
    # Module 2: Appointment & Booking Workflow
    story.append(Paragraph("3. Multi-Step Appointment & Booking Workflow", h1_style))
    story.append(Paragraph(
        "When a client books an appointment via the form or the Quick Create modal, the system enforces a structured status lifecycle to ensure clean operational tracking.",
        body_style
    ))
    
    # Status Table
    status_data = [
        [Paragraph("<b>Status</b>", h2_style), Paragraph("<b>Operational Meaning & Automated Action</b>", h2_style)],
        [Paragraph("<b>Draft</b>", body_style), Paragraph("Initial tentative booking created by receptionist. No confirmation emails are sent during this phase, protecting against premature client notifications.", body_style)],
        [Paragraph("<b>Confirmed</b>", body_style), Paragraph("Booking confirmed with client. <b>Automated Action:</b> The system instantly dispatches exactly ONE professional confirmation email (`Booking Confirmed`) containing service, staff, and date details.", body_style)],
        [Paragraph("<b>In Progress</b>", body_style), Paragraph("Client has arrived (`Arrived` checkbox set) and treatment is actively underway in the designated treatment room (`salon.room`).", body_style)],
        [Paragraph("<b>Done</b>", body_style), Paragraph("Service completed. Appointment is ready for POS checkout, or has been checked out and finalized.", body_style)],
        [Paragraph("<b>Cancelled</b>", body_style), Paragraph("Appointment cancelled. Slot is freed immediately on the visual calendar.", body_style)],
    ]
    t_status = Table(status_data, colWidths=[1.5*inch, 5.5*inch])
    t_status.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F1F5F9")),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_status)
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>3.1 Automated Email System & 30-Minute Reminders</b>", h2_style))
    story.append(Paragraph(
        "To guarantee a seamless customer experience, the suite features a robust two-stage email engine:<br/>"
        "1. <b>Single Confirmation Guarantee:</b> The system tracks email dispatch using a dedicated security flag (`confirmation_sent`). Whether an appointment is confirmed upon creation or via the <i>Confirm</i> button, exactly one confirmation email is sent.<br/>"
        "2. <b>Automated 30-Minute Reminder Cron:</b> A background scheduled task runs every 15 minutes, scanning all confirmed appointments scheduled to begin within the next 30 minutes. It automatically emails a gentle reminder (`email_template_appointment_reminder_30m`) and marks `reminder_sent_30m = True` to prevent duplicate alerts.",
        body_style
    ))
    story.append(Spacer(1, 15))
    
    # Module 3: Point of Sale (POS) Checkout & Tips
    story.append(Paragraph("4. Point of Sale (POS) Checkout & Tip Staff Integration", h1_style))
    story.append(Paragraph(
        "A standout feature of the suite is the seamless checkout flow between Salon Appointments and the Odoo 19 Point of Sale (POS) terminal.",
        body_style
    ))
    story.append(Paragraph("<b>4.1 The 'Tip Staff' POS Checkout Button</b>", h2_style))
    story.append(Paragraph(
        "During checkout, clients often wish to leave a gratuity (tip) for their beautician, stylist, or massage therapist via cash or credit card. Cashiers do not need to create complicated manual journal entries or generic tip items. Instead:",
        body_style
    ))
    story.append(Paragraph(
        "• <b>One-Click Selection:</b> Cashiers click the custom <b>Tip Staff</b> button located directly on the POS control panel.<br/>"
        "• <b>Beautician Selection Modal:</b> A visual pop-up displays all active salon staff members (`salon.staff`). The cashier selects the specific staff member receiving the tip.<br/>"
        "• <b>Custom Amount Entry:</b> The cashier inputs the exact tip amount (e.g., $15.00 or $50.00).<br/>"
        "• <b>Automated Line Tagging:</b> The POS attaches a special `Staff Tip` order line tagged with the exact `staff_id`. When the order is paid and finalized (`Paid / Done`), the backend automatically extracts this line and registers a formal `salon.staff.tip` database record linked to that beautician.",
        bullet_style
    ))
    story.append(Spacer(1, 10))
    
    # Module 4: Staff Profiles & Tip Settlement
    story.append(Paragraph("5. Beautician Profiles, Tip Settlement & Commissions", h1_style))
    story.append(Paragraph(
        "The <b>Staff Members</b> module (`salon.staff`) manages each beautician's schedule, allowed treatment capabilities, financial commissions, and tip balances.",
        body_style
    ))
    
    # Financial Table
    fin_data = [
        [Paragraph("<b>Financial Component</b>", h2_style), Paragraph("<b>Calculation & Settlement Mechanism</b>", h2_style)],
        [Paragraph("<b>Tip Records<br/>(`salon.staff.tip`)</b>", body_style), Paragraph("Every tip collected in POS generates an individual tip record containing the Date, POS Order Reference, Staff Member, Amount, and Status (`Unpaid` or `Paid`).", body_style)],
        [Paragraph("<b>Total Unpaid Tips Balance</b>", body_style), Paragraph("Each staff profile prominently displays their real-time pending balance (`Total Unpaid Tips`). Managers can view exactly how much gratuity is owed to each beautician at the end of their shift or pay period.", body_style)],
        [Paragraph("<b>One-Click Payout Settlement</b>", body_style), Paragraph("When disbursing cash or payroll tips, salon managers open the tip records and click <b>Mark Paid</b> (`action_mark_paid`). The unpaid balance instantly resets, maintaining a complete audit trail.", body_style)],
        [Paragraph("<b>Staff Commissions (`salon.commission`)</b>", body_style), Paragraph("Configurable commission percentages per service or staff member. When an appointment completes (`Done`), the system calculates the beautician's commission automatically for payroll tracking.", body_style)],
    ]
    t_fin = Table(fin_data, colWidths=[2.2*inch, 4.8*inch])
    t_fin.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F1F5F9")),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_fin)
    story.append(Spacer(1, 15))
    
    # Module 5: The Salon Dashboard
    story.append(Paragraph("6. The Real-Time Analytical Salon Dashboard", h1_style))
    story.append(Paragraph(
        "The <b>Dashboard</b> tab provides executive visibility into salon performance. With instant date filtering (<b>All Time, Today, This Week, This Month</b>), managers can evaluate operational health in real time.",
        body_style
    ))
    story.append(Paragraph("<b>6.1 Dashboard KPI Metrics</b>", h2_style))
    story.append(Paragraph(
        "• <b>Total Revenue & Payment Breakdown:</b> Displays overall gross revenue alongside exact splits between `Paid Revenue` (completed checkouts) and `Unpaid Revenue` (pending treatments).<br/>"
        "• <b>Appointment Volume & Status Distribution:</b> Shows total bookings and breaks down counts across `Draft`, `Confirmed`, `In Progress`, `Done`, and `Cancelled`.<br/>"
        "• <b>Average Booking Value & Customer Satisfaction:</b> Calculates average revenue per booking and aggregates client review star ratings (`1 to 5 Stars`).<br/>"
        "• <b>Total Tips & Commission Tracker:</b> A dedicated financial header displays `Total Tips Collected`, `Paid Tips Disbursed`, and `Pending Unpaid Tips` right alongside staff commission metrics.",
        bullet_style
    ))
    story.append(Paragraph("<b>6.2 Staff Performance Leaderboard</b>", h2_style))
    story.append(Paragraph(
        "The bottom of the dashboard features a dynamic leaderboard ranking all beauticians and therapists by revenue generated. For each staff member, it displays their Total Appointments, Completed Treatments, Gross Revenue, Earned Commissions, and <b>Total Tips Collected</b>.",
        body_style
    ))
    story.append(Spacer(1, 15))
    
    # Module 6: Additional Features
    story.append(Paragraph("7. Additional Advanced Modules & CRM Features", h1_style))
    story.append(Paragraph(
        "Beyond scheduling and POS, the suite includes powerful supplementary modules for comprehensive salon governance:",
        body_style
    ))
    story.append(Paragraph(
        "• <b>Room & Station Management (`salon.room`):</b> Assign specific treatment rooms, massage suites, or styling chairs to appointments to prevent physical double-booking.<br/>"
        "• <b>Client CRM & Treatment History (`salon.customer.history`):</b> Maintain detailed records of past color formulas, skin sensitivities, treatment preferences, and signed liability consent forms (`consent_signed`).<br/>"
        "• <b>Memberships & Packages (`salon.membership`, `salon.package`):</b> Offer recurring monthly VIP memberships or multi-session treatment packages (e.g., <i>Buy 5 Facials, Get 1 Free</i>).<br/>"
        "• <b>Client Feedback & Reviews (`salon.review`):</b> Collect post-appointment star ratings and client reviews to ensure top-tier service quality across all branches.",
        bullet_style
    ))
    story.append(Spacer(1, 20))
    
    # Conclusion
    story.append(HRFlowable(width="100%", thickness=1, color=c_border, spaceAfter=15))
    story.append(Paragraph("<b>System Verification & Deployment Status:</b> All modules, tip calculations, POS checkouts, and automated email confirmations have been fully compiled, upgraded, and verified on Odoo 19 database <code>spa_pos</code>.", callout_style))
    
    doc.build(story, canvasmaker=NumberedCanvas)
    print("PDF User Manual successfully generated at:", filename)

if __name__ == "__main__":
    build_pdf("/Users/developer/WS/odoo-19.0/custom-addons/testing-modules/salon_spa_scheduler/Salon_Spa_Scheduler_User_Manual.pdf")
