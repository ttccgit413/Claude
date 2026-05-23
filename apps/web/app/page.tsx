const AGENCY_NAME = process.env.NEXT_PUBLIC_AGENCY_NAME ?? "Mike's Social";
const AGENCY_EMAIL = process.env.NEXT_PUBLIC_AGENCY_EMAIL ?? "mike@youragency.com.au";
const AGENCY_CITY = "Melbourne, AU";

const STATS = [
  { value: "47", label: "Salons Audited" },
  { value: "12", label: "Active Clients" },
  { value: "144", label: "Posts Delivered" },
  { value: "+0.4★", label: "Avg Rating Lift" },
];

const STEPS = [
  {
    n: "1",
    title: "Free Audit",
    body: "We analyse your Google reviews, Instagram activity, and local competitors to find the gap.",
  },
  {
    n: "2",
    title: "AI-Crafted Content",
    body: "We produce 12 branded posts per month — captions, hashtags, and on-brand imagery — done for you.",
  },
  {
    n: "3",
    title: "Grow & Report",
    body: "Watch your follower count and Google rating climb. You get a live report page updated every month.",
  },
];

const VALUES = [
  {
    icon: "✂️",
    title: "Done-for-you Instagram",
    body: "You never touch a caption. We handle the full content calendar so you can stay in the chair.",
  },
  {
    icon: "📍",
    title: "Local SEO lift",
    body: "More reviews, better ratings, suburb-targeted hashtags — all working together to surface you in local search.",
  },
  {
    icon: "📊",
    title: "Month-by-month reporting",
    body: "A private client report page shows exactly what moved — followers, engagement, ratings — no spreadsheets.",
  },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50 font-sans">
      {/* Header */}
      <header className="sticky top-0 z-10 border-b bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <span className="text-sm font-semibold tracking-tight text-gray-900">
            {AGENCY_NAME}
          </span>
          <nav className="flex gap-6">
            <a
              href="#how-it-works"
              className="text-xs font-medium text-gray-500 hover:text-gray-900"
            >
              How it works
            </a>
            <a
              href="#results"
              className="text-xs font-medium text-gray-500 hover:text-gray-900"
            >
              Results
            </a>
            <a
              href={`mailto:${AGENCY_EMAIL}`}
              className="text-xs font-medium text-gray-900 hover:underline"
            >
              Contact
            </a>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section
        id="hero"
        className="px-6 py-20"
        style={{ background: "#C4A88218" }}
      >
        <div className="mx-auto max-w-3xl text-center">
          <p className="mb-4 text-xs font-medium uppercase tracking-widest text-gray-400">
            Social media for hair salons
          </p>
          <h1 className="mb-5 text-3xl font-bold leading-tight tracking-tight text-gray-900 sm:text-4xl">
            We grow your salon&apos;s Instagram
            <br className="hidden sm:block" /> while you stay in the chair.
          </h1>
          <p className="mx-auto mb-8 max-w-xl text-base text-gray-500">
            {AGENCY_NAME} is a boutique social media agency based in{" "}
            {AGENCY_CITY}. We handle content, hashtags, and monthly reporting
            for local hair salons — no lock-in contracts, no fluff.
          </p>
          <a
            href={`mailto:${AGENCY_EMAIL}?subject=Free salon audit`}
            className="inline-block rounded-xl bg-gray-900 px-8 py-3 text-sm font-semibold text-white transition-colors hover:bg-gray-700"
          >
            Book a free audit →
          </a>
        </div>
      </section>

      {/* Stats */}
      <section id="results" className="px-6 py-12">
        <div className="mx-auto max-w-3xl">
          <p className="mb-6 text-center text-xs font-medium uppercase tracking-widest text-gray-400">
            By the numbers
          </p>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {STATS.map((s) => (
              <div
                key={s.label}
                className="rounded-2xl border bg-white p-5 text-center"
              >
                <p className="text-3xl font-bold text-gray-900">{s.value}</p>
                <p className="mt-1 text-xs font-medium uppercase tracking-widest text-gray-400">
                  {s.label}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="px-6 py-12">
        <div className="mx-auto max-w-3xl">
          <p className="mb-6 text-center text-xs font-medium uppercase tracking-widest text-gray-400">
            How it works
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {STEPS.map((step) => (
              <div key={step.n} className="rounded-2xl border bg-white p-5">
                <span
                  className="mb-3 inline-flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold text-white"
                  style={{ background: "#C4A882" }}
                >
                  {step.n}
                </span>
                <h3 className="mb-2 text-sm font-semibold text-gray-900">
                  {step.title}
                </h3>
                <p className="text-sm leading-relaxed text-gray-500">
                  {step.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Value props */}
      <section className="px-6 py-12">
        <div className="mx-auto max-w-3xl">
          <p className="mb-6 text-center text-xs font-medium uppercase tracking-widest text-gray-400">
            What you get
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {VALUES.map((v) => (
              <div key={v.title} className="rounded-2xl border bg-white p-5">
                <p className="mb-3 text-2xl">{v.icon}</p>
                <h3 className="mb-2 text-sm font-semibold text-gray-900">
                  {v.title}
                </h3>
                <p className="text-sm leading-relaxed text-gray-500">{v.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA section */}
      <section className="px-6 py-12">
        <div className="mx-auto max-w-3xl">
          <div
            className="rounded-2xl p-10 text-center"
            style={{
              background: "#C4A88218",
              border: "1px solid #C4A88244",
            }}
          >
            <h2 className="mb-3 text-2xl font-bold text-gray-900">
              Ready to grow?
            </h2>
            <p className="mx-auto mb-7 max-w-md text-sm text-gray-500">
              Send us a quick email and we&apos;ll run a free audit of your
              salon&apos;s Instagram and Google presence — no obligation.
            </p>
            <a
              href={`mailto:${AGENCY_EMAIL}?subject=Free salon audit`}
              className="inline-block rounded-xl bg-gray-900 px-8 py-3 text-sm font-semibold text-white transition-colors hover:bg-gray-700"
            >
              Email {AGENCY_NAME} →
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t bg-white px-6 py-6">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          <p className="text-xs text-gray-400">
            © {new Date().getFullYear()} {AGENCY_NAME} · {AGENCY_CITY}
          </p>
          <a
            href="/review"
            className="text-xs text-gray-300 hover:text-gray-500"
          >
            Admin
          </a>
        </div>
      </footer>
    </div>
  );
}
