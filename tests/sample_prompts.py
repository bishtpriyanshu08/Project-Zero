# =============================================================================
# sample_prompts.py — Evaluation Dataset
# =============================================================================
# Contains 10 normal prompts and 10 edge-case prompts for testing the
# AI App Generator pipeline. These prompts cover a range of application
# types and difficulty levels.
#
# Normal prompts: Well-defined, realistic application descriptions
# Edge cases: Vague, conflicting, or incomplete descriptions that test
#             the system's robustness and assumption-handling
# =============================================================================


# =============================================================================
# 10 Normal Prompts — Clear, well-defined application descriptions
# =============================================================================

NORMAL_PROMPTS = [
    {
        "name": "CRM System",
        "prompt": (
            "Build a CRM system with user login, contact management, a dashboard "
            "with analytics, role-based access control, and premium subscriptions. "
            "Admins can view analytics and manage all contacts. Regular users can "
            "only manage their own contacts."
        ),
    },
    {
        "name": "E-Commerce Store",
        "prompt": (
            "Create an e-commerce store with product catalog, shopping cart, "
            "checkout with payment processing, order tracking, user reviews, "
            "and an admin panel for inventory management. Support customer and "
            "admin roles. Include search and filtering for products."
        ),
    },
    {
        "name": "Hospital Management",
        "prompt": (
            "Build a hospital management system with patient registration, "
            "doctor scheduling, appointment booking, medical records management, "
            "prescription tracking, billing, and an admin dashboard. Roles include "
            "admin, doctor, nurse, and patient. Doctors can view patient records "
            "and write prescriptions."
        ),
    },
    {
        "name": "School Portal",
        "prompt": (
            "Create a school management portal with student enrollment, teacher "
            "management, class scheduling, grade tracking, attendance management, "
            "parent notifications, and report card generation. Roles: admin, teacher, "
            "student, parent. Teachers can enter grades and take attendance."
        ),
    },
    {
        "name": "Inventory System",
        "prompt": (
            "Build an inventory management system with product tracking, stock "
            "level monitoring, supplier management, purchase orders, low-stock "
            "alerts, barcode scanning support, and reporting. Roles: admin, "
            "warehouse manager, staff. Managers can approve purchase orders."
        ),
    },
    {
        "name": "Expense Tracker",
        "prompt": (
            "Create a personal and team expense tracker with expense logging, "
            "receipt upload, category management, monthly budgets, spending "
            "analytics with charts, and export to CSV. Roles: admin, manager, "
            "employee. Managers can approve expenses over $100."
        ),
    },
    {
        "name": "Fitness App",
        "prompt": (
            "Build a fitness tracking app with workout logging, exercise library, "
            "progress tracking with charts, goal setting, nutrition tracking, "
            "meal plans, and social features like sharing achievements. Roles: "
            "admin, trainer, user. Trainers can create workout plans for users."
        ),
    },
    {
        "name": "Hotel Booking",
        "prompt": (
            "Create a hotel booking system with room management, reservation "
            "calendar, guest check-in/check-out, payment processing, review "
            "system, and a dashboard showing occupancy rates. Roles: admin, "
            "receptionist, guest. Receptionists can manage check-ins."
        ),
    },
    {
        "name": "Job Portal",
        "prompt": (
            "Build a job portal with job posting, application tracking, resume "
            "upload, company profiles, job search with filters, application "
            "status tracking, and messaging between employers and candidates. "
            "Roles: admin, employer, candidate. Employers can post jobs and "
            "review applications."
        ),
    },
    {
        "name": "Library Management",
        "prompt": (
            "Create a library management system with book catalog, member "
            "registration, book borrowing and returns, fine calculation, "
            "reservation system, and overdue notifications. Roles: admin, "
            "librarian, member. Librarians can manage the catalog and process "
            "borrow/return transactions."
        ),
    },
]


# =============================================================================
# 10 Edge-Case Prompts — Vague, conflicting, or incomplete descriptions
# =============================================================================

EDGE_CASE_PROMPTS = [
    {
        "name": "Vague - Build Something Useful",
        "prompt": "Build something useful.",
    },
    {
        "name": "Minimal - Make an App",
        "prompt": "Make an app.",
    },
    {
        "name": "Conflicting Requirements",
        "prompt": (
            "Build a system where admins cannot access the admin panel. "
            "Users should have full control but no permissions. The app "
            "should be both public and require authentication."
        ),
    },
    {
        "name": "Missing Authentication",
        "prompt": (
            "Create a multi-user project management tool with team workspaces, "
            "task assignments, and role-based dashboards. Don't include any "
            "login or authentication system."
        ),
    },
    {
        "name": "Undefined Entities",
        "prompt": (
            "Build an app that manages things. Users can create, edit, and "
            "delete stuff. There should be a dashboard showing the data "
            "and some reports."
        ),
    },
    {
        "name": "Ambiguous Users",
        "prompt": (
            "Create a platform for people. Some people manage other people. "
            "There are different levels of people with different abilities. "
            "Include a way to track what people do."
        ),
    },
    {
        "name": "Contradictory Permissions",
        "prompt": (
            "Build a document management system. All users can delete everything "
            "but no user should be able to modify anything. Viewers have write "
            "access and editors can only read. Admins have no special privileges."
        ),
    },
    {
        "name": "Incomplete Payment Flow",
        "prompt": (
            "Create a subscription service with premium tiers. Include billing "
            "but don't track payments. Users can upgrade their plan but there's "
            "no payment method. Show payment history without recording transactions."
        ),
    },
    {
        "name": "Missing Workflows",
        "prompt": (
            "Build a task management system. There are tasks. Tasks have status. "
            "Tasks belong to projects. That's it."
        ),
    },
    {
        "name": "Unclear Business Rules",
        "prompt": (
            "Build an app with complex business logic. The rules are dynamic "
            "and change based on context. Some features are only available "
            "sometimes. Access depends on multiple factors that aren't specified."
        ),
    },
]


# =============================================================================
# Combined list for easy iteration
# =============================================================================

ALL_PROMPTS = NORMAL_PROMPTS + EDGE_CASE_PROMPTS
