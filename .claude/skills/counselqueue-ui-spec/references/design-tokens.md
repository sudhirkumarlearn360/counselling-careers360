# Design tokens (copied from prototypes)

Fonts (Google Fonts): `https://fonts.googleapis.com/css2?family=Instrument+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Instrument+Serif:ital@0;1&display=swap`: Instrument Sans for UI, Instrument Serif for display.

The staff console and hall board use the navy palette below. The student flow layers the Careers360 warm palette (`--c360-*`) on top of it. Its primary CTA uses the brand gradient `linear-gradient(120deg,#C0392B 0%,#E85D3A 55%,#F39C12 100%)`, and the topbar uses `linear-gradient(90deg,#B03020 0%,#C0392B 40%,#D4500E 100%)`. Both support dark mode through `prefers-color-scheme` and a `data-theme` override.

## Staff console / base (`CounselQueue — staff console.html`)
```css
:root{
  --navy:#12356B; --blue:#2B6CB8; --sky:#E9F1FB; --paper:#F4F8FD; --card:#FFFFFF;
  --amber:#D98A16; --amber-soft:#FBEFD9; --rose:#B3261E; --rose-soft:#FBE7E5;
  --ink:#0F1F35; --muted:#5A6D85; --line:#DCE6F2; --line-strong:#BFD0E4;
  --ok:#12795C; --ok-soft:#DDF1EA;
  --r-s:6px; --r-m:12px; --r-l:20px;
  --sans:"Instrument Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --serif:"Instrument Serif",Georgia,"Times New Roman",serif;
  --shadow:0 1px 2px rgba(18,43,39,.06),0 8px 24px -16px rgba(18,43,39,.35);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --navy:#8FB8EC; --blue:#A8CBF3; --sky:#16273D; --paper:#0A1626; --card:#122238;
    --ink:#E6EEF8; --muted:#9AAEC6; --line:#22354F; --line-strong:#33496A;
    --amber-soft:#3A2D10; --rose-soft:#3B1B18; --ok-soft:#0F2E26;
  }
}
:root[data-theme="dark"]{
  --navy:#8FB8EC; --blue:#A8CBF3; --sky:#16273D; --paper:#0A1626; --card:#122238;
  --ink:#E6EEF8; --muted:#9AAEC6; --line:#22354F; --line-strong:#33496A;
  --amber-soft:#3A2D10; --rose-soft:#3B1B18; --ok-soft:#0F2E26;
}
```

## Student check-in brand (`Careers360 counselling — student check-in.html`)
```css
:root{
  /* Careers360 brand — softened for student-facing UI */
  --c360-red:#C0392B;   --c360-red-d:#992D22;
  --c360-rose:#E85D4A;  /* lighter warm red for accents */
  --c360-gold:#F39C12;  --c360-gold-lt:#F8C76A;
  --c360-peach:#FF7F5C; /* mid-point in the gradient */
  --c360-cream:#FFFBF8; --c360-warm:#FFF3EF;
  --c360-step-line:#F5C6BE; --c360-sel-bg:#FFF0EC;
  --c360-text-on-grad:#fff;
}
```
