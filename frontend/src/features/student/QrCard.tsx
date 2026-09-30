import QRCode from "qrcode";
import { useEffect, useState } from "react";

/** A real, scannable QR for the centre's check-in page (the prototype drew a decorative one). */
export function QrCard({ url }: { url: string }) {
  const [src, setSrc] = useState("");
  useEffect(() => {
    let live = true;
    QRCode.toString(url, { type: "svg", margin: 0, errorCorrectionLevel: "M", color: { dark: "#0f1f35", light: "#0000" } })
      .then((svg) => live && setSrc(`data:image/svg+xml;utf8,${encodeURIComponent(svg)}`))
      .catch(() => live && setSrc(""));
    return () => {
      live = false;
    };
  }, [url]);
  return (
    <div className="land-qr">
      {src ? <img src={src} alt={`QR code that opens ${url}`} width={150} height={150} /> : <div className="qr-ph" aria-hidden="true" />}
      <div>
        <div className="qt"><span aria-hidden="true">📱 </span>Scan to check in</div>
        <div className="qd">Point your phone camera at the code. Opens the form instantly — no app needed.</div>
      </div>
    </div>
  );
}
