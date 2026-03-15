"use client";
import Link from "next/link";
import styles from "./page.module.css";

export default function HomePage() {
  return (
    <div className={styles.page}>
      {/* Nav */}
      <nav className={styles.nav}>
        <div className={styles.logo}>
          pay<span>verify</span>
        </div>
        <div className={styles.navLinks}>
          <Link href="#how">How it works</Link>
          <Link href="/admin" className={styles.navAdmin}>Admin</Link>
        </div>
      </nav>

      {/* Hero */}
      <section className={styles.hero}>
        <div className={styles.pill}>
          Easypaisa &middot; JazzCash &middot; Meezan
        </div>
        <h1 className={styles.h1}>
          Fee verification<br />
          made <em>instant</em>
        </h1>
        <p className={styles.sub}>
          Students pay as usual via any Pakistani bank app. Enter your
          transaction ID and we confirm your fee payment in seconds —
          no phone calls, no waiting in queues.
        </p>
        <div className={styles.ctaRow}>
          <Link href="/verify" className={styles.ctaPrimary}>
            Verify my payment
          </Link>
          <Link href="/admin" className={styles.ctaSecondary}>
            Admin dashboard
          </Link>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className={styles.steps}>
        {[
          {
            n: "01",
            title: "Pay normally",
            desc: "Send your fee via Easypaisa, JazzCash, or Meezan to the school's account as usual.",
          },
          {
            n: "02",
            title: "Get your TxnID",
            desc: "The payment app sends you a confirmation SMS. Copy the Transaction ID from that message.",
          },
          {
            n: "03",
            title: "Verify here",
            desc: "Paste your Transaction ID below. We match it instantly and email you a receipt.",
          },
        ].map((s) => (
          <div key={s.n} className={styles.stepCard}>
            <div className={styles.stepNum}>{s.n}</div>
            <div className={styles.stepTitle}>{s.title}</div>
            <div className={styles.stepDesc}>{s.desc}</div>
          </div>
        ))}
      </section>

      {/* Banks */}
      <section className={styles.banks}>
        {["Easypaisa", "JazzCash", "Meezan Bank"].map((b) => (
          <div key={b} className={styles.bankChip}>{b}</div>
        ))}
      </section>

      {/* CTA banner */}
      <section className={styles.banner}>
        <div className={styles.bannerText}>Ready to verify your payment?</div>
        <Link href="/verify" className={styles.ctaPrimary}>
          Start verification &rarr;
        </Link>
      </section>

      <footer className={styles.footer}>
        &copy; {new Date().getFullYear()} PayVerify &mdash; Built for schools
      </footer>
    </div>
  );
}
