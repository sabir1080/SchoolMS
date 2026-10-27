import qrcode from "qrcode-generator";

import { BrandLogo } from "@/components/BrandLogo";
import { formatDate } from "@/lib/navigation";

export interface IdCardData {
  id: number;
  full_name: string;
  admission_no: string;
  photo: string;
  date_of_birth: string | null;
  blood_group: string;
  class_name: string | null;
  roll_number: string;
  valid_until: string | null;
  guardian_name: string;
  guardian_relation: string;
  guardian_phone: string;
}

export interface IdCardInstitute {
  name: string;
  address: string;
  phone: string;
  code: string;
}

qrcode.stringToBytes = qrcode.stringToBytesFuncs["UTF-8"];

/** QR code as an SVG data URL; scanning it shows who the card belongs to. */
function qrFor(card: IdCardData, institute: IdCardInstitute) {
  const text = [
    institute.name,
    `Student: ${card.full_name}`,
    `Admission No: ${card.admission_no}`,
    card.class_name &&
      `Class: ${card.class_name}${card.roll_number ? ` (Roll ${card.roll_number})` : ""}`,
    card.guardian_phone && `Parent: ${card.guardian_phone}`,
  ]
    .filter(Boolean)
    .join("\n");
  const qr = qrcode(0, "M");
  qr.addData(text);
  qr.make();
  return `data:image/svg+xml;utf8,${encodeURIComponent(qr.createSvgTag({ cellSize: 2, margin: 0, scalable: true }))}`;
}

/** One student ID card, front and back, at the standard card size (85.6 × 54 mm). */
export function IdCard({
  card,
  institute,
  logo,
  classLabel,
}: {
  card: IdCardData;
  institute: IdCardInstitute;
  logo: string | undefined;
  classLabel: string;
}) {
  const initials = card.full_name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("");
  const rows: [string, string][] = [
    ["Adm. No.", card.admission_no],
    ...(card.class_name
      ? [
          [
            classLabel,
            card.class_name +
              (card.roll_number ? ` · Roll ${card.roll_number}` : ""),
          ] as [string, string],
        ]
      : []),
    ...(card.guardian_name
      ? [
          [card.guardian_relation || "Parent", card.guardian_name] as [
            string,
            string,
          ],
        ]
      : []),
    ...(card.date_of_birth
      ? [["Date of birth", formatDate(card.date_of_birth)] as [string, string]]
      : []),
    ...(card.blood_group
      ? [["Blood group", card.blood_group] as [string, string]]
      : []),
  ];
  const face =
    "id-card relative h-[54mm] w-[85.6mm] shrink-0 overflow-hidden rounded-[3mm] border border-slate-300 bg-white text-slate-900";

  return (
    <div
      className="id-card-pair flex flex-wrap gap-[4mm]"
      data-testid="id-card"
    >
      <div className={face}>
        <div className="flex h-[12mm] items-center gap-[2mm] bg-brand-600 px-[3mm] text-white">
          <BrandLogo
            src={logo}
            className="h-[8mm] w-[8mm] rounded-full bg-white p-[0.5mm]"
          />
          <div className="min-w-0 leading-tight">
            <p className="truncate text-[11px] font-bold">{institute.name}</p>
            <p className="text-[7px] tracking-wider uppercase opacity-90">
              Student identity card
            </p>
          </div>
        </div>
        <div className="flex gap-[3mm] px-[3mm] pt-[2.5mm]">
          {card.photo ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={card.photo}
              alt=""
              className="h-[26mm] w-[21mm] shrink-0 rounded-[1.5mm] border border-slate-200 object-cover"
            />
          ) : (
            <div className="flex h-[26mm] w-[21mm] shrink-0 items-center justify-center rounded-[1.5mm] border border-dashed border-slate-300 text-lg font-semibold text-slate-400">
              {initials}
            </div>
          )}
          <div className="min-w-0 flex-1">
            <p className="truncate text-[12px] leading-tight font-bold">
              {card.full_name}
            </p>
            <dl className="mt-[1mm] space-y-[0.4mm] text-[7.5px] leading-tight">
              {rows.map(([k, v]) => (
                <div key={k} className="flex gap-[1mm]">
                  <dt className="w-[15mm] shrink-0 text-slate-500">{k}</dt>
                  <dd className="truncate font-medium">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
        <div className="absolute inset-x-0 bottom-0 h-[1.5mm] bg-brand-600" />
      </div>

      <div className={face}>
        <div className="flex h-full gap-[3mm] p-[3mm] pb-[4mm]">
          <div className="flex min-w-0 flex-1 flex-col text-[7.5px] leading-snug">
            <p className="font-semibold">If found, please return to:</p>
            <p className="font-bold">{institute.name}</p>
            {institute.address && (
              <p className="text-slate-600">{institute.address}</p>
            )}
            {institute.phone && (
              <p className="text-slate-600">Phone: {institute.phone}</p>
            )}
            {card.guardian_phone && (
              <p className="mt-[1.5mm]">
                Parent contact:{" "}
                <span className="font-semibold">{card.guardian_phone}</span>
              </p>
            )}
            {card.valid_until && (
              <p className="mt-auto">
                Valid until: {formatDate(card.valid_until)}
              </p>
            )}
            <p className="mt-[3mm] border-t border-slate-400 pt-[0.5mm] text-center text-[6.5px] text-slate-500">
              Principal&apos;s signature
            </p>
          </div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={qrFor(card, institute)}
            alt="QR code"
            className="h-[22mm] w-[22mm] shrink-0 self-center"
          />
        </div>
        <div className="absolute inset-x-0 bottom-0 h-[1.5mm] bg-brand-600" />
      </div>
    </div>
  );
}
