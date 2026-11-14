export function AegisLogo({ className = "h-7 w-7" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      className={className}
      aria-hidden
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle cx="16" cy="16" r="14" stroke="#55B8E8" strokeWidth="1.25" opacity="0.9" />
      <ellipse
        cx="16"
        cy="16"
        rx="14"
        ry="6"
        stroke="#55B8E8"
        strokeWidth="1"
        transform="rotate(-28 16 16)"
        opacity="0.85"
      />
      <circle cx="24" cy="10" r="2.2" fill="#55B8E8" />
      <circle cx="16" cy="16" r="2" fill="#E7EEF5" />
    </svg>
  );
}
