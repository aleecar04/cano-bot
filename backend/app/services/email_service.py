import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings


def _smtp_enabled() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def send_verification_email(to_email: str, first_name: str | None, code: str) -> None:
    if not _smtp_enabled():
        print(f"[EMAIL] Código de verificación para {to_email}: {code}")
        return

    name = first_name or "usuario"
    subject = "Tu código de verificación — CANOBOT"

    # Spaced code for better readability in plaintext
    spaced = " ".join(code)
    plain = (
        f"Hola {name},\n\n"
        f"Tu código de verificación de CANOBOT es:\n\n"
        f"  {spaced}\n\n"
        f"Válido durante 15 minutos.\n\n"
        f"Si no solicitaste este código, ignora este mensaje.\n\n"
        f"— El equipo de CANOBOT"
    )

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Código de verificación · CANOBOT</title>
</head>
<body style="margin:0;padding:0;background:#0f172a;font-family:'Segoe UI',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
         style="background:#0f172a;padding:48px 16px;">
    <tr>
      <td align="center">
        <table width="520" cellpadding="0" cellspacing="0" role="presentation"
               style="background:#1e293b;border-radius:20px;border:1px solid #334155;
                      overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,0.5);">

          <!-- Top accent bar -->
          <tr>
            <td style="height:4px;background:linear-gradient(90deg,#4f46e5,#818cf8,#6366f1);
                       font-size:0;line-height:0;">&nbsp;</td>
          </tr>

          <!-- Header -->
          <tr>
            <td style="background:#0f172a;padding:32px 40px 28px;text-align:center;">
              <div style="display:inline-block;background:#1e293b;border:1px solid #334155;
                          border-radius:14px;padding:10px 22px;">
                <span style="font-size:22px;font-weight:900;color:#f1f5f9;
                             letter-spacing:-0.5px;vertical-align:middle;">
                  ⚡&thinsp;CANO<span style="color:#818cf8;">BOT</span>
                </span>
              </div>
              <p style="margin:14px 0 0;color:#475569;font-size:12px;letter-spacing:0.5px;">
                Asistente domótico inteligente
              </p>
            </td>
          </tr>

          <!-- Divider -->
          <tr>
            <td style="padding:0 40px;">
              <div style="height:1px;background:#334155;font-size:0;">&nbsp;</div>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px 40px 32px;">

              <p style="margin:0 0 6px;font-size:20px;font-weight:700;color:#f1f5f9;">
                Hola, {name} 👋
              </p>
              <p style="margin:0 0 32px;color:#64748b;font-size:14px;line-height:1.7;">
                Alguien (esperamos que tú) ha creado una cuenta en CANOBOT con esta
                dirección de correo. Introduce el código de abajo para confirmarla.
              </p>

              <!-- Code box -->
              <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
                     style="margin-bottom:32px;">
                <tr>
                  <td style="background:#0f172a;border:1px solid #4f46e5;border-radius:16px;
                             padding:28px 24px;text-align:center;">
                    <p style="margin:0 0 12px;color:#818cf8;font-size:10px;font-weight:700;
                               letter-spacing:3px;text-transform:uppercase;">
                      Código de verificación
                    </p>
                    <span style="font-size:48px;font-weight:900;color:#f1f5f9;
                                 letter-spacing:14px;font-family:'Courier New',monospace;
                                 display:inline-block;padding-left:14px;">
                      {code}
                    </span>
                    <p style="margin:16px 0 0;color:#475569;font-size:12px;">
                      Expira en&nbsp;<strong style="color:#94a3b8;">15 minutos</strong>
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Warning note -->
              <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                <tr>
                  <td style="background:#1e293b;border:1px solid #334155;border-left:3px solid #4f46e5;
                             border-radius:8px;padding:12px 16px;">
                    <p style="margin:0;color:#64748b;font-size:12px;line-height:1.6;">
                      Si no has solicitado este código, alguien puede haber introducido tu
                      correo por error. Puedes ignorar este mensaje de forma segura.
                    </p>
                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#0f172a;padding:20px 40px;text-align:center;
                       border-top:1px solid #1e293b;">
              <p style="margin:0 0 4px;color:#334155;font-size:11px;letter-spacing:0.3px;">
                © 2026 CANOBOT &mdash; Mensaje automático, no respondas a este correo.
              </p>
              <p style="margin:0;color:#1e293b;font-size:10px;">
                ⚡ CANOBOT
              </p>
            </td>
          </tr>

          <!-- Bottom accent bar -->
          <tr>
            <td style="height:3px;background:linear-gradient(90deg,#6366f1,#4f46e5);
                       font-size:0;line-height:0;">&nbsp;</div></td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html,  "html",  "utf-8"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.ehlo()
        if settings.SMTP_TLS:
            server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.EMAILS_FROM_EMAIL, to_email, msg.as_string())
