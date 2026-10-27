/** The institute's logo (a small data URL saved with the institute, so next/image is not needed). */
export function BrandLogo({ src, className = "h-10 w-10" }: { src: string | null | undefined; className?: string }) {
  if (!src) return null;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt="" className={`${className} shrink-0 object-contain`} />;
}
