export function CyPlanAILogoSVG({
  className,
  width,
  height,
}: {
  width?: number;
  height?: number;
  className?: string;
}) {
  const size = width || height || 32;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <defs>
        <linearGradient id="cyplanaiBgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#14b8a6" stopOpacity={1} />
          <stop offset="100%" stopColor="#0d9488" stopOpacity={1} />
        </linearGradient>
        <linearGradient id="cyplanaiShieldGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#ffffff" stopOpacity={1} />
          <stop offset="100%" stopColor="#e0f2fe" stopOpacity={1} />
        </linearGradient>
      </defs>
      
      {/* Main background circle */}
      <circle cx="32" cy="32" r="30" fill="url(#cyplanaiBgGradient)"/>
      
      {/* Shield shape (cybersecurity symbol) */}
      <path 
        d="M32 12 L20 18 L20 28 C20 36 24 42 32 46 C40 42 44 36 44 28 L44 18 Z" 
        fill="url(#cyplanaiShieldGradient)" 
        stroke="#0f766e" 
        strokeWidth="1.5"
      />
      
      {/* AI/Neural network nodes inside shield */}
      <circle cx="28" cy="26" r="2.5" fill="#14b8a6"/>
      <circle cx="36" cy="26" r="2.5" fill="#14b8a6"/>
      <circle cx="32" cy="32" r="2.5" fill="#14b8a6"/>
      <circle cx="28" cy="36" r="2.5" fill="#14b8a6"/>
      <circle cx="36" cy="36" r="2.5" fill="#14b8a6"/>
      
      {/* Connection lines (neural network) */}
      <path d="M28 26 L32 32" stroke="#14b8a6" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M36 26 L32 32" stroke="#14b8a6" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M32 32 L28 36" stroke="#14b8a6" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M32 32 L36 36" stroke="#14b8a6" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M28 26 L36 26" stroke="#14b8a6" strokeWidth="1" strokeLinecap="round" opacity="0.6"/>
      <path d="M28 36 L36 36" stroke="#14b8a6" strokeWidth="1" strokeLinecap="round" opacity="0.6"/>
      
      {/* Small accent dots for detail */}
      <circle cx="24" cy="22" r="1" fill="#ffffff" opacity="0.8"/>
      <circle cx="40" cy="22" r="1" fill="#ffffff" opacity="0.8"/>
    </svg>
  );
}

