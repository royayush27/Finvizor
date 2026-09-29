import Link from "next/link";

export default function WelcomePage() {
  return (
    <div className="overview">
      <div className="eyebrow">US EQUITIES / PORTFOLIO RESEARCH</div>
      <div className="overview-intro">
        <div>
          <h1>A portfolio starts<br />with a point of view.</h1>
          <p className="intro-copy">Choose the businesses you want to own. Set your tolerance for risk. Then examine how the pieces fit together.</p>
          <Link href="/industry-focus" className="primary-button">Build a portfolio <span aria-hidden="true">↗</span></Link>
          <p className="caption mt-4">US stocks · USD allocations · Historical market data</p>
        </div>
        <div className="research-note">
          <span className="eyebrow">THE WORKING PRINCIPLE</span>
          <p>Know what you own.<br /><em>Understand the trade-offs.</em></p>
          <div className="note-rule" />
          <span className="text-sm leading-relaxed">Returns tell one part of the story. Concentration, volatility and your time horizon tell the rest.</span>
        </div>
      </div>
      <section className="process-section" aria-labelledby="process-title">
        <div><span className="eyebrow">YOUR RESEARCH, IN ORDER</span><h2 id="process-title">From preferences<br />to positions.</h2></div>
        <div className="process-list">
          <Link href="/industry-focus"><span>01</span><div><h3>Define your universe</h3><p>Focus on sectors you understand, or leave the screen broad.</p></div><b aria-hidden="true">↗</b></Link>
          <Link href="/risk-assessment"><span>02</span><div><h3>Put risk in context</h3><p>Bring your experience, goals and investment horizon into the decision.</p></div><b aria-hidden="true">↗</b></Link>
          <Link href="/portfolio-builder"><span>03</span><div><h3>Inspect the allocation</h3><p>Screen stocks or choose your own. Review weights, historical returns and portfolio risk.</p></div><b aria-hidden="true">↗</b></Link>
        </div>
      </section>
      <section className="method-note"><h2>Evidence before expectations.</h2><p>Finvizor uses historical prices to help you explore allocations. Results are research illustrations, not validated forecasts or investment recommendations. Prices may be delayed; no trades are placed.</p></section>
    </div>
  );
}
