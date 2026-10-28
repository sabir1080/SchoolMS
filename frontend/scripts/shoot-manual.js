// Refresh the user manual's screenshots: run against a local API with the demo seeded (python manage.py seed_demo,
// TZ=Asia/Karachi) and the static site served on :3000, then: node scripts/shoot-manual.js
const { chromium, devices } = require('playwright');
const base = 'http://localhost:3000';
const API = 'http://localhost:8000';
const OUT = require('path').join(__dirname, '..', 'public', 'manual');
const log = (m) => console.log('✓ ' + m);

async function token(username) {
  const r = await fetch(API + '/api/auth/login/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ institute_code: 'demo', username, password: 'demo1234' }) });
  return (await r.json()).access;
}
async function get(path, t) {
  const r = await fetch(API + path, { headers: { Authorization: `Bearer ${t}` } });
  const d = await r.json();
  return d.results || d;
}

(async () => {
  const T = await token('admin');
  const exams = await get('/api/exams/', T);
  const published = exams.find((e) => e.status === 'published');
  const sections = await get('/api/academics/sections/', T);
  const students = await get('/api/students/', T);
  const invoices = await get('/api/fees/invoices/?status=partial', T);
  const anyInvoice = invoices[0] || (await get('/api/fees/invoices/', T))[0];

  const browser = await chromium.launch();
  const phone = { ...devices['iPhone 13'], deviceScaleFactor: 1.5 };
  const session = async (user) => {
    const ctx = await browser.newContext(phone);
    const page = await ctx.newPage();
    if (user) {
      await page.goto(base + '/login/?code=demo');
      await page.getByLabel('Username or email', { exact: true }).fill(user);
      await page.getByLabel('Password', { exact: true }).fill('demo1234');
      await page.click('button:has-text("Sign in")');
      await page.waitForURL('**/dashboard/');
    }
    return page;
  };
  // Scroll the part to show near the top, then save what is on screen.
  const shot = async (page, name, { top, wait } = {}) => {
    if (wait) await page.waitForSelector(wait);
    if (top) {
      await page.locator(top).first().evaluate((el) => window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 70));
    }
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${OUT}/${name}.jpg`, type: 'jpeg', quality: 72, clip: { x: 0, y: 0, width: 390, height: 760 } });
    log(name);
  };

  const guest = await session(null);
  await guest.goto(base + '/login/?code=demo');
  await shot(guest, 'login', { wait: 'button:has-text("Sign in")' });

  const admin = await session('admin');
  await shot(admin, 'first-setup-dashboard', { wait: 'text=Welcome' });
  await admin.goto(base + '/academics/?tab=programs');
  await shot(admin, 'first-setup', { wait: 'text=Class 3' });
  await admin.goto(base + `/students/view/?id=${students[0].id}`);
  await shot(admin, 'students', { wait: 'text=Parents / guardians' });
  await admin.goto(base + '/admissions/');
  await admin.click('main li button:has-text("Hania")');
  await shot(admin, 'online-admission', { wait: 'button:has-text("Admit student")', top: 'main li:has(button:has-text("Admit student"))' });
  await admin.goto(base + `/fees/invoice/?id=${anyInvoice.id}`);
  await shot(admin, 'fees', { wait: 'text=Receive payment' });
  await admin.goto(base + '/settings/');
  await admin.waitForSelector('button:has-text("Save JazzCash")');
  await shot(admin, 'online-pay', { top: 'h2:text-is("Online fee payments")' });
  await admin.goto(base + `/exams/results/?id=${published.id}&section=${sections[0].id}`);
  await shot(admin, 'exams', { wait: 'text=Pass rate' });
  await admin.goto(base + `/timetable/`);
  await shot(admin, 'timetable', { wait: 'text=Teacher timetable' });
  await admin.goto(base + '/messages/');
  await shot(admin, 'messages', { wait: 'text=Messages to parents' });
  await admin.goto(base + '/payroll/');
  await shot(admin, 'staff', { wait: 'text=Monthly salaries' });
  // Only in this local copy: a next session, so the promotion page has somewhere to move students.
  const current = (await get('/api/academics/sessions/', T)).find((x) => x.is_current);
  const y = Number(current.end_date.slice(0, 4));
  await fetch(API + '/api/academics/sessions/', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${T}` },
    body: JSON.stringify({ name: `${y}-${String(y + 1).slice(2)}`, start_date: `${y}-04-01`, end_date: `${y + 1}-03-31`, is_current: false }) });
  await admin.goto(base + '/students/promotion/');
  await admin.locator('label:has(> span:text-is("Section")) select').selectOption({ label: 'Class 3 - A' });
  await admin.waitForSelector('text=Suggestions from');
  await shot(admin, 'year-end', { top: 'label:has(> span:text-is("Section"))' });
  await admin.goto(base + '/reports/');
  await admin.click('text=Fee dues');
  await admin.click('button:has-text("Show report"):not([disabled])');
  await shot(admin, 'reports', { wait: 'text=Download Excel' });
  await admin.goto(base + '/billing/');
  await shot(admin, 'plan', { wait: 'text=Current plan' });

  const teacher = await session('sana');
  await shot(teacher, 'teacher-day', { wait: 'text=Welcome' });
  await teacher.goto(base + '/attendance/');
  await shot(teacher, 'attendance', { wait: 'button:has-text("Save attendance")' });

  const parent = await session('rashid');
  await parent.evaluate(() => {
    const e = new Event('beforeinstallprompt');
    e.prompt = async () => {};
    e.userChoice = Promise.resolve({ outcome: 'dismissed' });
    window.dispatchEvent(e);
  });
  await parent.click('button:has-text("Menu")');
  await shot(parent, 'install', { wait: 'text=Install app on this phone' });
  await parent.click('button:has-text("Menu")');
  await shot(parent, 'family', { wait: 'text=My children', top: 'text=My children' });

  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
