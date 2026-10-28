/** Content of the user manual (/manual), in English and Roman Urdu. Button names match the app exactly. */

export type Lang = "en" | "ur";
export type Audience = "all" | "admin" | "teacher" | "family";
type Text = Record<Lang, string>;

export interface ManualSection {
  id: string;
  icon: string;
  audience: Audience;
  title: Text;
  intro: Text;
  steps: Record<Lang, string[]>;
  tip?: Text;
  /** Screenshots from the demo school (public/manual/<file>.jpg, phone size). */
  images?: { file: string; caption: Text }[];
}

export const AUDIENCES: { value: Audience | "every"; label: Text }[] = [
  { value: "every", label: { en: "Everything", ur: "Sab kuch" } },
  { value: "admin", label: { en: "School admin", ur: "School admin" } },
  { value: "teacher", label: { en: "Teacher", ur: "Teacher" } },
  { value: "family", label: { en: "Parent & student", ur: "Parent aur student" } },
];

export const AUDIENCE_BADGE: Record<Audience, Text> = {
  all: { en: "Everyone", ur: "Sab ke liye" },
  admin: { en: "Admin", ur: "Admin" },
  teacher: { en: "Teacher", ur: "Teacher" },
  family: { en: "Parent & student", ur: "Parent aur student" },
};

export const MANUAL: ManualSection[] = [
  {
    id: "login",
    images: [
      { file: "login", caption: { en: "The sign-in screen after entering the institute code.", ur: "Institute code ke baad sign in ki screen." } },
    ],
    icon: "key",
    audience: "all",
    title: { en: "Logging in", ur: "Login karna" },
    intro: {
      en: "Everyone logs in with the institute code, then their own username and password.",
      ur: "Har shakhs pehle institute code, phir apna username aur password daal kar login karta hai.",
    },
    steps: {
      en: [
        "Open the app link and type your institute code (your school gives it to you, e.g. demo). Tap Continue.",
        "Type your username or email and your password. Tap the eye button to see what you typed. Tap Sign in.",
        "The phone remembers the institute code. To use another one, tap Change next to the code.",
        "Forgot your password? Ask your institute admin: they open Users and tap Reset password.",
        "Change your own password any time from the menu: Change password.",
      ],
      ur: [
        "App ka link kholein aur institute code likhein (ye aap ka school deta hai, maslan demo). Continue dabayein.",
        "Apna username ya email aur password likhein. Aankh wala button dabane se likha hua nazar aata hai. Sign in dabayein.",
        "Phone institute code yaad rakhta hai. Doosra code istemal karna ho to code ke saath Change dabayein.",
        "Password bhool gaye? Apne institute admin se kahein: woh Users mein ja kar Reset password dabayenge.",
        "Apna password kabhi bhi menu se badal sakte hain: Change password.",
      ],
    },
    tip: {
      en: "If you see “Your login has expired”, just sign in again. Logins stay active for 7 days of use.",
      ur: "Agar “Your login has expired” likha aaye to dobara sign in kar lein. Login 7 din tak chalta rehta hai.",
    },
  },
  {
    id: "install",
    images: [
      { file: "install", caption: { en: "Menu with “Install app on this phone” and “Help & manual”.", ur: "Menu mein “Install app on this phone” aur “Help & manual”." } },
    ],
    icon: "phone",
    audience: "all",
    title: { en: "Install the app and turn on notifications", ur: "App install karna aur notifications on karna" },
    intro: {
      en: "SchoolMS works in the phone's browser and can be installed like an app, with free notifications.",
      ur: "SchoolMS phone ke browser mein chalta hai aur app ki tarah install ho sakta hai, free notifications ke saath.",
    },
    steps: {
      en: [
        "Android (Chrome): open the menu and tap Install app on this phone, then Install.",
        "iPhone (Safari): tap the Share button, then Add to Home Screen.",
        "Parents and students: on the dashboard tap Turn on notifications and allow them.",
        "Anyone can turn them on or off later from Change password → Phone notifications. Send a test checks it works.",
      ],
      ur: [
        "Android (Chrome): menu kholein aur Install app on this phone dabayein, phir Install.",
        "iPhone (Safari): Share button dabayein, phir Add to Home Screen.",
        "Parents aur students: dashboard par Turn on notifications dabayein aur ijazat (Allow) de dein.",
        "Baad mein Change password → Phone notifications se on ya off kar sakte hain. Send a test se check ho jata hai.",
      ],
    },
    tip: {
      en: "On iPhone, notifications work only after adding the app to the Home Screen (iOS 16.4 or newer).",
      ur: "iPhone par notifications sirf tab aati hain jab app Home Screen par add ho (iOS 16.4 ya naya).",
    },
  },
  {
    id: "first-setup",
    images: [
      { file: "first-setup-dashboard", caption: { en: "The admin dashboard.", ur: "Admin ka dashboard." } },
      { file: "first-setup", caption: { en: "Academic setup → Classes.", ur: "Academic setup → Classes." } },
    ],
    icon: "rocket",
    audience: "admin",
    title: { en: "First-time setup (admin)", ur: "Pehli dafa setup (admin)" },
    intro: {
      en: "Do these once, in this order. The dashboard's Get started list shows what is left.",
      ur: "Ye kaam aik dafa, isi tarteeb se karein. Dashboard par Get started list batati hai kya baqi hai.",
    },
    steps: {
      en: [
        "Register: on the login page tap New institute? Register, fill the form and tap Create institute & start trial.",
        "Institute settings: check name, phone and address (they print on report cards, receipts and certificates).",
        "Optional: rename “Class” and “Section” (e.g. Grade, Batch) in Institute settings → Names used in your institute.",
        "Logo and theme colour (Pro plan): Institute settings → Logo and theme colour → Upload logo, pick a colour, Save.",
        "Academic setup → Sessions → Add session (e.g. 2026-27) and mark it current.",
        "Academic setup → Subjects → Add subjects (you can paste many at once).",
        "Academic setup → Classes: add classes and tick their subjects. Then add sections (A, B…) with a class teacher.",
        "Users → Add user for each teacher (role Teacher), so they can log in.",
      ],
      ur: [
        "Register: login page par New institute? Register dabayein, form bharein aur Create institute & start trial dabayein.",
        "Institute settings: naam, phone aur pata check karein (ye report card, raseed aur certificate par chhapte hain).",
        "Chahein to “Class” aur “Section” ka naam badlein (maslan Grade, Batch): Institute settings → Names used in your institute.",
        "Logo aur rang (Pro plan): Institute settings → Logo and theme colour → Upload logo, rang chunein, Save.",
        "Academic setup → Sessions → Add session (maslan 2026-27) aur use current banayein.",
        "Academic setup → Subjects → Add subjects (aik saath kai naam paste kar sakte hain).",
        "Academic setup → Classes: classes banayein aur un ke subjects tick karein. Phir sections (A, B…) class teacher ke saath banayein.",
        "Users → Add user har teacher ke liye (role Teacher), taake woh login kar sakein.",
      ],
    },
  },
  {
    id: "students",
    images: [
      { file: "students", caption: { en: "A student's page: photo, ID card, certificate and edit.", ur: "Student ka page: photo, ID card, certificate aur edit." } },
    ],
    icon: "users",
    audience: "admin",
    title: { en: "Students and admissions", ur: "Students aur admission" },
    intro: {
      en: "Add students, link parents, give logins, photos and ID cards.",
      ur: "Students add karein, parents jorein, login, photo aur ID card banayein.",
    },
    steps: {
      en: [
        "Students → + New admission. Fill the student's details, the class/section and roll number, and the parent's name and phone. Save.",
        "The admission number is made automatically (you can type your own).",
        "Open a student → Add photo to add a photo (it is made small automatically).",
        "Parent login: on the student's page, under Parents / guardians, tap Create login, choose a username and password and give them to the parent.",
        "Student login (optional): Student login → Create login.",
        "ID card: on the student's page tap ID card → Print / Save PDF. For a whole class: Students → ID cards → choose the class.",
        "To move a student to another class: Change class on the student's page.",
      ],
      ur: [
        "Students → + New admission. Student ki maloomat, class/section, roll number aur parent ka naam aur phone bharein. Save.",
        "Admission number khud ban jata hai (chahein to apna likh sakte hain).",
        "Student kholein → Add photo se photo lagayein (khud chhoti ho jati hai).",
        "Parent ka login: student ke page par Parents / guardians mein Create login dabayein, username aur password rakh kar parent ko de dein.",
        "Student ka login (zaroori nahi): Student login → Create login.",
        "ID card: student ke page par ID card → Print / Save PDF. Poori class ke liye: Students → ID cards → class chunein.",
        "Class badalni ho to student ke page par Change class dabayein.",
      ],
    },
  },
  {
    id: "online-admission",
    images: [
      { file: "online-admission", caption: { en: "An application opened on the Admissions page.", ur: "Admissions page par khuli hui application." } },
    ],
    icon: "form",
    audience: "admin",
    title: { en: "Online admission form", ur: "Online admission form" },
    intro: {
      en: "Parents can apply from their phones; you admit or decline in one tap.",
      ur: "Parents phone se apply kar sakte hain; aap aik tap mein admit ya decline karte hain.",
    },
    steps: {
      en: [
        "Menu → Admissions → Open the form.",
        "Share the link: Copy link or Share on WhatsApp. Parents also see “Apply for admission” on your login page.",
        "New applications appear under New. Tap one to see the details.",
        "Choose the class - section and roll number, then Admit student: the student, the parent and the class are created and the parent gets a message.",
        "Or write a reason and tap Decline.",
        "Tap Close the form when admissions are over.",
      ],
      ur: [
        "Menu → Admissions → Open the form.",
        "Link share karein: Copy link ya Share on WhatsApp. Parents ko login page par bhi “Apply for admission” nazar aata hai.",
        "Nayi applications New mein aati hain. Kisi par tap karke tafseel dekhein.",
        "Class - section aur roll number chunein, phir Admit student: student, parent aur class ban jaate hain aur parent ko message jata hai.",
        "Ya wajah likh kar Decline dabayein.",
        "Admission khatam hon to Close the form dabayein.",
      ],
    },
  },
  {
    id: "attendance",
    images: [
      { file: "attendance", caption: { en: "Taking attendance: tap Absent, Leave or Late, then Save attendance.", ur: "Haazri: Absent, Leave ya Late dabayein, phir Save attendance." } },
    ],
    icon: "check",
    audience: "teacher",
    title: { en: "Daily attendance", ur: "Rozana haazri" },
    intro: {
      en: "Class teachers (and admins) mark attendance once a day.",
      ur: "Class teacher (aur admin) din mein aik dafa haazri lagate hain.",
    },
    steps: {
      en: [
        "Menu → Attendance. Your section and today's date are chosen for you.",
        "Everyone starts as present: tap Absent, Leave or Late for the others.",
        "Tap Save attendance. Parents of absent students get an alert the same day.",
        "Made a mistake? Change it and save again: a child marked present again gets no alert.",
        "Admins see on the dashboard which sections have not marked attendance yet.",
      ],
      ur: [
        "Menu → Attendance. Aap ka section aur aaj ki tareekh pehle se chuni hoti hai.",
        "Sab present se shuru hote hain: baqi ke liye Absent, Leave ya Late dabayein.",
        "Save attendance dabayein. Ghair-haazir bachon ke parents ko usi din alert chala jata hai.",
        "Ghalti ho gayi? Badal kar dobara save karein: dobara present kiye gaye bachche ka alert nahi jata.",
        "Admin dashboard par dekh sakta hai kis section ki haazri abhi nahi lagi.",
      ],
    },
  },
  {
    id: "fees",
    images: [
      { file: "fees", caption: { en: "A bill with a payment and its Receipt link.", ur: "Bill, payment aur us ki Receipt ka link." } },
    ],
    icon: "wallet",
    audience: "admin",
    title: { en: "Fees, bills and receipts", ur: "Fees, bill aur raseed" },
    intro: {
      en: "Set fees once, then create everyone's monthly bills in one tap.",
      ur: "Fees aik dafa set karein, phir sab ke mahana bill aik tap mein banayein.",
    },
    steps: {
      en: [
        "Fees → Fee setup: add fee types (Tuition Fee, Admission Fee…) and the amount for each class. Copy from last session saves time.",
        "Discounts: on a student's page add a concession (amount or percent).",
        "Fees → Overview → Create monthly bills: choose the month, issue date and due date → Create bills.",
        "Receiving cash: Fees → Invoices → open the bill → enter the amount, method and date → Save payment.",
        "Tap Receipt next to a payment to print it; the parent also gets a thank-you message with the receipt number.",
        "One-off bills (trip, uniform): Fees → Invoices → + One-off bill.",
        "Overview shows billed, received and still due, and the students with the biggest overdue amounts.",
      ],
      ur: [
        "Fees → Fee setup: fee ki qismein (Tuition Fee, Admission Fee…) aur har class ki raqam daalein. Copy from se pichhle session ki fees copy ho jati hai.",
        "Riyayat: student ke page par concession (raqam ya percent) daalein.",
        "Fees → Overview → Create monthly bills: mahina, issue date aur due date chunein → Create bills.",
        "Naqad wasooli: Fees → Invoices → bill kholein → raqam, tareeqa aur tareekh likhein → Save payment.",
        "Payment ke saath Receipt dabayein aur print karein; parent ko raseed number ke saath shukriya ka message bhi jata hai.",
        "Alag bill (trip, uniform): Fees → Invoices → + One-off bill.",
        "Overview mein kitna bill hua, kitna mila, kitna baqi, aur sab se zyada baqaya wale bachche nazar aate hain.",
      ],
    },
    tip: {
      en: "Overdue reminders to parents: Messages → Send fee reminders (at most once a day).",
      ur: "Baqaya fees ki yaad-dihani: Messages → Send fee reminders (din mein zyada se zyada aik dafa).",
    },
  },
  {
    id: "online-pay",
    images: [
      { file: "online-pay", caption: { en: "Institute settings → Online fee payments.", ur: "Institute settings → Online fee payments." } },
    ],
    icon: "card",
    audience: "admin",
    title: { en: "Online fee payments", ur: "Online fees ki adaigi" },
    intro: {
      en: "Parents can pay with JazzCash, Easypaisa, Safepay or a card (Stripe). Money goes straight to your own merchant account.",
      ur: "Parents JazzCash, Easypaisa, Safepay ya card (Stripe) se fees de sakte hain. Paisa seedha aap ke apne merchant account mein jata hai.",
    },
    steps: {
      en: [
        "Get a merchant account from the gateway you want (they give you the keys).",
        "Institute settings → Online fee payments → fill the keys for that gateway. Keep Test mode on until the gateway says your account is live.",
        "Give the gateway the addresses shown under “Addresses to give …” (where needed).",
        "Tick Show to parents and Save. Parents now see Pay with … buttons on unpaid bills.",
        "A payment is recorded only after the gateway confirms it; the bill becomes Paid and a receipt is made.",
      ],
      ur: [
        "Jis gateway se lena hai us se merchant account lein (woh aap ko keys dete hain).",
        "Institute settings → Online fee payments → us gateway ki keys bharein. Jab tak gateway account live na kare, Test mode on rakhein.",
        "“Addresses to give …” mein diye gaye pate gateway ko de dein (jahan zaroorat ho).",
        "Show to parents tick karein aur Save. Ab parents ko unpaid bills par Pay with … buttons nazar aayenge.",
        "Payment tabhi record hoti hai jab gateway tasdeeq kare; bill Paid ho jata hai aur raseed ban jati hai.",
      ],
    },
  },
  {
    id: "exams",
    images: [
      { file: "exams", caption: { en: "Exam result with pass rate, positions and report cards.", ur: "Imtihan ka result: pass rate, position aur report cards." } },
    ],
    icon: "clipboard",
    audience: "admin",
    title: { en: "Exams, marks and report cards", ur: "Imtihan, marks aur report card" },
    intro: {
      en: "Create an exam, let teachers enter marks, publish the result and print report cards.",
      ur: "Imtihan banayein, teachers marks dalein, result publish karein aur report card print karein.",
    },
    steps: {
      en: [
        "Exams → + New exam: name, dates and classes → Create exam. Papers are added for each subject (100 marks, pass marks from your pass percentage).",
        "Adjust marks, date and time per paper and print the Date sheet. Grading lets you change the grade scale.",
        "When the exam is over tap Open marks entry.",
        "Teachers (or you): Exams → the exam → Marks entry → choose section and subject → type marks or tick Absent → Save marks.",
        "The exam page shows how many marks are entered per section.",
        "Tap Publish result: marks lock, results and positions are worked out, and parents get the result by message.",
        "Results → print the result sheet or Report card for each student (one A4 page).",
        "Annual result: Exams → Annual result → + Annual result → choose exams and weightage (e.g. 25/25/50) → Create annual result.",
      ],
      ur: [
        "Exams → + New exam: naam, tareekhein aur classes → Create exam. Har subject ka paper khud ban jata hai (100 marks, pass marks aap ke pass percentage se).",
        "Har paper ke marks, tareekh aur waqt badlein aur Date sheet print karein. Grading se grade scale badal sakte hain.",
        "Imtihan khatam ho to Open marks entry dabayein.",
        "Teacher (ya aap): Exams → imtihan → Marks entry → section aur subject chunein → marks likhein ya Absent tick karein → Save marks.",
        "Imtihan ke page par har section ke marks kitne aa chuke, nazar aata hai.",
        "Publish result dabayein: marks lock ho jaate hain, result aur position ban jaati hai, aur parents ko result ka message jata hai.",
        "Results → result sheet ya har bachche ka Report card print karein (aik A4 safha).",
        "Saalana result: Exams → Annual result → + Annual result → imtihan aur weightage chunein (maslan 25/25/50) → Create annual result.",
      ],
    },
  },
  {
    id: "teacher-day",
    images: [
      { file: "teacher-day", caption: { en: "A teacher's dashboard.", ur: "Teacher ka dashboard." } },
    ],
    icon: "book",
    audience: "teacher",
    title: { en: "A teacher's day", ur: "Teacher ka din" },
    intro: {
      en: "Everything a teacher needs is in the menu after logging in.",
      ur: "Teacher ki zaroorat ki har cheez login ke baad menu mein hai.",
    },
    steps: {
      en: [
        "Dashboard: today's classes from the timetable.",
        "Attendance: mark your section (class teachers).",
        "Homework → Add to diary: date, section, subject, homework and details → Save. Previous day / Next day moves through the diary.",
        "Exams → Marks entry: you see only the subjects you teach (from the timetable) and your own section's subjects if you are its class teacher.",
        "Timetable → My timetable: your whole week.",
        "My salary slips: your monthly slips (when the school uses payroll).",
      ],
      ur: [
        "Dashboard: timetable se aaj ki classes.",
        "Attendance: apne section ki haazri (class teacher).",
        "Homework → Add to diary: tareekh, section, subject, homework aur tafseel → Save. Previous day / Next day se diary aage peeche hoti hai.",
        "Exams → Marks entry: sirf woh subjects nazar aate hain jo aap parhate hain (timetable se), aur class teacher hon to apne section ke sab subjects.",
        "Timetable → My timetable: aap ka poora hafta.",
        "My salary slips: aap ki mahana salary slips (agar school payroll istemal karta hai).",
      ],
    },
  },
  {
    id: "timetable",
    images: [
      { file: "timetable", caption: { en: "A class timetable, day by day.", ur: "Class ka timetable, din ba din." } },
    ],
    icon: "calendar",
    audience: "admin",
    title: { en: "Timetable", ur: "Timetable" },
    intro: {
      en: "Make periods once, then fill each section's week.",
      ur: "Periods aik dafa banayein, phir har section ka hafta bharein.",
    },
    steps: {
      en: [
        "Timetable → Periods & days → Quick setup: school starts, minutes each, number of periods and the break → Create periods. Tick the school days.",
        "Timetable → choose a section → tap a cell → choose subject and teacher → Save.",
        "A teacher cannot be put in two classes at the same time; the app tells you.",
        "Teacher timetable shows any teacher's week.",
      ],
      ur: [
        "Timetable → Periods & days → Quick setup: school ka waqt, har period ke minute, periods ki tadaad aur break → Create periods. School ke din tick karein.",
        "Timetable → section chunein → khane par tap → subject aur teacher chunein → Save.",
        "Aik teacher aik waqt mein do classes mein nahi lag sakta; app bata deti hai.",
        "Teacher timetable mein kisi bhi teacher ka hafta nazar aata hai.",
      ],
    },
  },
  {
    id: "messages",
    images: [
      { file: "messages", caption: { en: "Messages to parents with “Send on WhatsApp”.", ur: "Parents ke messages, “Send on WhatsApp” ke saath." } },
    ],
    icon: "chat",
    audience: "admin",
    title: { en: "Messages to parents", ur: "Parents ko messages" },
    intro: {
      en: "Absence alerts, fee reminders, results, homework and notices reach parents by WhatsApp/SMS and phone notification.",
      ur: "Ghair-haazri, fees ki yaad-dihani, result, homework aur notice parents tak WhatsApp/SMS aur phone notification se pohanchte hain.",
    },
    steps: {
      en: [
        "Messages shows the outbox: To send, Sent and Failed.",
        "Free WhatsApp (default): tap Send on WhatsApp on each message; WhatsApp opens with the text ready. The message then counts as sent.",
        "Automatic sending: Message settings → How to send → Twilio, fill the Twilio details → Save settings.",
        "Choose which alerts go automatically under Automatic alerts.",
        "Notice to all parents (or one section): Write a notice → Add notice.",
      ],
      ur: [
        "Messages mein outbox hai: To send, Sent aur Failed.",
        "Free WhatsApp (pehle se): har message par Send on WhatsApp dabayein; WhatsApp tayyar text ke saath khulta hai. Phir message sent shumar hota hai.",
        "Khud-ba-khud bhejna: Message settings → How to send → Twilio, Twilio ki maloomat bharein → Save settings.",
        "Automatic alerts mein chunein kaun se alerts khud jayen.",
        "Sab parents (ya aik section) ko notice: Write a notice → Add notice.",
      ],
    },
  },
  {
    id: "staff",
    images: [
      { file: "staff", caption: { en: "Monthly salaries: paid and to pay.", ur: "Mahana tankhwah: di gayi aur baqi." } },
    ],
    icon: "briefcase",
    audience: "admin",
    title: { en: "Staff and salaries", ur: "Staff aur tankhwah" },
    intro: { en: "Keep staff records and make salary slips every month.", ur: "Staff ka record rakhein aur har mahine salary slip banayein." },
    steps: {
      en: [
        "Staff & payroll → + Add staff member: name, designation, basic salary, allowance (link a teacher's login if they have one) → Save.",
        "Monthly salaries → choose the month → Make salaries for … (slips for everyone in one tap).",
        "Add bonus or deduction on a slip, then Mark paid (cash, bank, JazzCash, Easypaisa).",
        "Print a slip from the slip page. Teachers see their own under My salary slips.",
      ],
      ur: [
        "Staff & payroll → + Add staff member: naam, ohda, basic salary, allowance (teacher ka login ho to jor dein) → Save.",
        "Monthly salaries → mahina chunein → Make salaries for … (sab ki slips aik tap mein).",
        "Slip par bonus ya katauti daalein, phir Mark paid (cash, bank, JazzCash, Easypaisa).",
        "Slip ke page se print karein. Teachers apni slips My salary slips mein dekhte hain.",
      ],
    },
  },
  {
    id: "year-end",
    images: [
      { file: "year-end", caption: { en: "Promotion suggestions from the result.", ur: "Result se promotion ke mashware." } },
    ],
    icon: "arrow",
    audience: "admin",
    title: { en: "Year end: promotion and certificates", ur: "Saal ka aakhir: promotion aur certificates" },
    intro: { en: "Move students to the next class and issue certificates.", ur: "Bachon ko agli class mein bhejein aur certificates dein." },
    steps: {
      en: [
        "First add the new session in Academic setup → Sessions.",
        "Students → Promote to next class → choose the section, From session and To session.",
        "Each student gets a suggestion from the annual (or last) result: Promote or Same class. Change any to Left the school or Graduated, then Apply.",
        "Certificates: on a student's page tap Certificate → choose Character, School leaving or Bonafide → Issue certificate → Print.",
        "A leaving certificate can mark the student as left at the same time.",
      ],
      ur: [
        "Pehle Academic setup → Sessions mein naya session banayein.",
        "Students → Promote to next class → section, From session aur To session chunein.",
        "Har bachche ke liye saalana (ya aakhri) result se mashwara aata hai: Promote ya Same class. Chahein to Left the school ya Graduated karein, phir Apply.",
        "Certificate: student ke page par Certificate → Character, School leaving ya Bonafide chunein → Issue certificate → Print.",
        "Leaving certificate ke saath bachche ko left bhi mark kiya ja sakta hai.",
      ],
    },
  },
  {
    id: "reports",
    images: [
      { file: "reports", caption: { en: "A report with Download Excel and Print / Save PDF.", ur: "Report, Download Excel aur Print / Save PDF ke saath." } },
    ],
    icon: "chart",
    audience: "admin",
    title: { en: "Reports (Excel and PDF)", ur: "Reports (Excel aur PDF)" },
    intro: { en: "Ready-made reports to view, download or print.", ur: "Tayyar reports dekhein, download karein ya print karein." },
    steps: {
      en: [
        "Menu → Reports → choose: Student list, Monthly attendance, Fee dues, Fee collection, Exam result sheet or Salaries.",
        "Choose the filters (class, month, exam) → Show report.",
        "Download Excel saves a spreadsheet; Print / Save PDF prints it.",
      ],
      ur: [
        "Menu → Reports → chunein: Student list, Monthly attendance, Fee dues, Fee collection, Exam result sheet ya Salaries.",
        "Filters chunein (class, mahina, imtihan) → Show report.",
        "Download Excel se spreadsheet aati hai; Print / Save PDF se print hota hai.",
      ],
    },
  },
  {
    id: "family",
    images: [
      { file: "family", caption: { en: "A parent's dashboard: children, attendance and fees.", ur: "Parent ka dashboard: bachche, haazri aur fees." } },
    ],
    icon: "home",
    audience: "family",
    title: { en: "For parents and students", ur: "Parents aur students ke liye" },
    intro: {
      en: "Your dashboard shows everything about your child; a parent with two children sees both.",
      ur: "Dashboard par bachche ki har maloomat hai; do bachon wale parent ko dono nazar aate hain.",
    },
    steps: {
      en: [
        "Attendance: today, this month and the whole session.",
        "Fees: what is due. Tap Pay with … (when the school offers online payment) and follow the steps. Tap Receipt to see or save a receipt.",
        "Results: published exam results and the annual result; open the report card to print or save it as PDF.",
        "Homework and timetable: the diary day by day and the class timetable.",
        "Turn on notifications to get absence, fee, result and homework alerts on your phone.",
      ],
      ur: [
        "Haazri: aaj, is mahine aur poore session ki.",
        "Fees: kitni baqi hai. Pay with … dabayein (agar school online adaigi deta hai) aur steps follow karein. Receipt se raseed dekhein ya save karein.",
        "Results: publish shuda imtihan ke results aur saalana result; report card khol kar print ya PDF save karein.",
        "Homework aur timetable: din ba din diary aur class ka timetable.",
        "Turn on notifications dabayein taake haazri, fees, result aur homework ke alerts phone par aayein.",
      ],
    },
  },
  {
    id: "plan",
    images: [
      { file: "plan", caption: { en: "Plan & Billing.", ur: "Plan & Billing." } },
    ],
    icon: "star",
    audience: "admin",
    title: { en: "Plan, billing and users", ur: "Plan, billing aur users" },
    intro: { en: "Your subscription and who can log in.", ur: "Aap ki subscription aur kaun login kar sakta hai." },
    steps: {
      en: [
        "Plan & Billing shows your plan, days left, student and staff limits.",
        "To upgrade or renew: tap Choose (or Renew) on a plan, pick monthly or yearly, fill in your details, read the subscription agreement and sign by typing your name.",
        "Pay using the details shown under “How to pay” and add the payment reference. We record the payment, your plan starts and the agreement shows as Active with the paid period.",
        "Your agreements lists the free trial and every subscription agreement: tap View to read or print one.",
        "Users → Add user for admins and teachers; Reset password for anyone who forgot theirs.",
        "Institute settings → Password rules chooses how strong new passwords must be.",
      ],
      ur: [
        "Plan & Billing mein aap ka plan, baqi din, students aur staff ki had nazar aati hai.",
        "Upgrade ya renew: plan par Choose (ya Renew) dabayein, monthly ya yearly chunein, apni maloomat bharein, subscription agreement parhein aur apna naam likh kar sign karein.",
        "“How to pay” mein diye gaye tareeqe se payment karein aur reference likh dein. Hum payment record karte hain, plan chalu ho jata hai aur agreement Active (paid period ke saath) ho jata hai.",
        "Your agreements mein free trial aur har subscription ka agreement hai: View se parhein ya print karein.",
        "Users → Add user admins aur teachers ke liye; password bhoolne wale ke liye Reset password.",
        "Institute settings → Password rules se naye passwords ki mazbooti chunein.",
      ],
    },
  },
  {
    id: "backup",
    icon: "cloud",
    audience: "admin",
    title: { en: "Data backup and recycle bin", ur: "Data backup aur recycle bin" },
    intro: {
      en: "Keep your own copy of your institute's data, and bring back things deleted by mistake.",
      ur: "Apne institute ke data ki apni copy rakhein, aur ghalti se delete hui cheezen wapas layein.",
    },
    steps: {
      en: [
        "Institute settings → Data backup → Download backup saves a file with all your data (students, fees, results, attendance, staff and settings). Keep it in Google Drive.",
        "Download in Excel gives sheets you can open yourself: students, bills, payments, results, attendance and staff.",
        "The card shows when you last downloaded a backup; download one every month. If your plan has expired, the same card is on Plan & Billing.",
        "If something goes wrong with your data: Data backup → Restore from a backup → choose your backup file → Check file. You see how many records there are now and after the restore. Type your institute code and tap Restore now.",
        "Your data from before the restore is saved under Copies saved before a restore; Put back undoes the restore. Only an unchanged file downloaded from your own institute is accepted; plan, payments and agreements do not change.",
        "Recycle bin (admin menu): a deleted student, payment, homework, exam, staff member, certificate or other record stays here for 30 days. Tap Restore to bring it back with everything deleted with it, or Delete for good.",
      ],
      ur: [
        "Institute settings → Data backup → Download backup se aik file save hoti hai jis mein aap ka sara data hai (students, fees, results, haazri, staff aur settings). Ise Google Drive mein rakhein.",
        "Download in Excel se sheets milti hain jo aap khud khol sakte hain: students, bills, payments, results, haazri aur staff.",
        "Card par likha hota hai ke aakhri backup kab liya; har mahine aik backup lein. Plan khatam ho jaye to yehi card Plan & Billing par hota hai.",
        "Agar data mein koi masla ho jaye: Data backup → Restore from a backup → apni backup file chunein → Check file. Abhi aur restore ke baad kitna data hoga, dikh jata hai. Institute code likhein aur Restore now dabayein.",
        "Restore se pehle ka data Copies saved before a restore mein mehfooz hota hai; Put back se restore wapas ho jata hai. Sirf apne institute ki asli (badli na gayi) file chalti hai; plan, payments aur agreements nahi badalte.",
        "Recycle bin (admin menu): delete kiya gaya student, payment, homework, imtihan, staff, certificate waghera 30 din yahan rehta hai. Restore se woh apni sab mutaliqa cheezon ke saath wapas aa jata hai, ya Delete for good.",
      ],
    },
    tip: {
      en: "The backup file does not contain your payment gateway keys, so it is safe to keep in your own Drive. Passwords go back to what they were on the backup date after a restore.",
      ur: "Backup file mein payment gateway ki keys nahi hotin, is liye apni Drive mein rakhna mehfooz hai. Restore ke baad passwords backup wale din jaise ho jate hain.",
    },
  },
];

export const FAQ: { q: Text; a: Text }[] = [
  {
    q: { en: "The app takes long to open the first time.", ur: "App pehli dafa khulne mein der lagati hai." },
    a: {
      en: "On the free server it can take up to a minute to wake up after a quiet time. After that it is fast.",
      ur: "Free server kuch der khamosh rehne ke baad jaagne mein aik minute tak le sakta hai. Phir tez chalta hai.",
    },
  },
  {
    q: { en: "“Institute code not found”", ur: "“Institute code not found”" },
    a: {
      en: "Check the spelling with your school. Tap Use a different institute code to type it again.",
      ur: "Apne school se spelling check karein. Use a different institute code daba kar dobara likhein.",
    },
  },
  {
    q: { en: "A parent did not get the absence alert.", ur: "Parent ko ghair-haazri ka alert nahi mila." },
    a: {
      en: "Check the parent's phone number on the student's page and the Messages outbox (Failed / To send).",
      ur: "Student ke page par parent ka phone number aur Messages ka outbox (Failed / To send) check karein.",
    },
  },
  {
    q: { en: "Can I fix marks after publishing?", ur: "Publish ke baad marks theek ho sakte hain?" },
    a: {
      en: "Yes: on the exam tap Back to preparing or Open marks entry, fix the marks, then publish again.",
      ur: "Haan: imtihan par Back to preparing ya Open marks entry dabayein, marks theek karein, phir dobara publish karein.",
    },
  },
  {
    q: { en: "Is our data safe?", ur: "Kya hamara data mehfooz hai?" },
    a: {
      en: "Each institute sees only its own data. Online payments count only after the gateway confirms them. You can download your own backup any time, and deleted records stay in the Recycle bin for 30 days.",
      ur: "Har institute sirf apna data dekhta hai. Online payment tabhi maani jati hai jab gateway tasdeeq kare. Aap jab chahein apna backup download kar sakte hain, aur delete hui cheezen 30 din Recycle bin mein rehti hain.",
    },
  },
];
