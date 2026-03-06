import React from 'react';

type IconProps = {
  className?: string;
  size?: number;
};

const Svg = ({
  children,
  className,
  size = 18,
}: IconProps & { children: React.ReactNode }) => (
  <svg
    className={className}
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {children}
  </svg>
);

export const IconUserCircle = (props: IconProps) => (
  <Svg {...props}>
    <circle cx="12" cy="12" r="9" />
    <circle cx="12" cy="9" r="2.5" />
    <path d="M7.5 17.2C8.6 15.4 10.2 14.5 12 14.5C13.8 14.5 15.4 15.4 16.5 17.2" />
  </Svg>
);

export const IconSettings = (props: IconProps) => (
  <Svg {...props}>
    <circle cx="12" cy="12" r="2.6" />
    <path d="M19 12a7 7 0 0 0-.08-1l2.04-1.58-1.7-2.94-2.45.85a7.2 7.2 0 0 0-1.73-1L14.7 3h-3.4l-.38 2.33a7.2 7.2 0 0 0-1.73 1l-2.45-.85-1.7 2.94L7.08 11a7 7 0 0 0 0 2l-2.04 1.58 1.7 2.94 2.45-.85a7.2 7.2 0 0 0 1.73 1L11.3 21h3.4l.38-2.33a7.2 7.2 0 0 0 1.73-1l2.45.85 1.7-2.94L18.92 13c.05-.33.08-.66.08-1Z" />
  </Svg>
);

export const IconGlobe = (props: IconProps) => (
  <Svg {...props}>
    <circle cx="12" cy="12" r="9" />
    <path d="M3 12h18" />
    <path d="M12 3a14 14 0 0 1 0 18" />
    <path d="M12 3a14 14 0 0 0 0 18" />
  </Svg>
);

export const IconBot = (props: IconProps) => (
  <Svg {...props}>
    <rect x="5.5" y="7" width="13" height="11" rx="3" />
    <path d="M12 4v3" />
    <circle cx="9.3" cy="12" r="1" />
    <circle cx="14.7" cy="12" r="1" />
    <path d="M9.5 15h5" />
  </Svg>
);

export const IconScroll = (props: IconProps) => (
  <Svg {...props}>
    <path d="M7 4.5h9a2 2 0 0 1 2 2V17a2.5 2.5 0 1 1-2.5-2.5H8.5A2.5 2.5 0 1 0 11 17V6.5A2 2 0 0 0 9 4.5H7z" />
    <path d="M9 8h6" />
    <path d="M9 11h6" />
  </Svg>
);

export const IconInfoCircle = (props: IconProps) => (
  <Svg {...props}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 10v6" />
    <circle cx="12" cy="7.2" r="0.8" fill="currentColor" stroke="none" />
  </Svg>
);

export const IconClose = (props: IconProps) => (
  <Svg {...props}>
    <path d="M6 6l12 12" />
    <path d="M18 6L6 18" />
  </Svg>
);

export const IconBulb = (props: IconProps) => (
  <Svg {...props}>
    <path d="M8.5 10.2A3.5 3.5 0 1 1 15 12.1c-.5.8-1.1 1.5-1.7 2.1-.4.4-.6.9-.6 1.4H11.3c0-.6-.2-1.1-.6-1.5-.5-.5-1-1.1-1.5-1.8-.5-.7-.7-1.4-.7-2.1Z" />
    <path d="M10 18h4" />
    <path d="M10.5 20h3" />
  </Svg>
);

export const IconPlus = (props: IconProps) => (
  <Svg {...props}>
    <path d="M12 5v14" />
    <path d="M5 12h14" />
  </Svg>
);

export const IconSparkles = (props: IconProps) => (
  <Svg {...props}>
    <path d="M12 4l1.2 2.8L16 8l-2.8 1.2L12 12l-1.2-2.8L8 8l2.8-1.2L12 4Z" />
    <path d="M18 13l.7 1.6L20.3 15l-1.6.7L18 17.3l-.7-1.6L15.7 15l1.6-.7L18 13Z" />
    <path d="M6 13l.7 1.6L8.3 15l-1.6.7L6 17.3l-.7-1.6L3.7 15l1.6-.7L6 13Z" />
  </Svg>
);

export const IconTrash = (props: IconProps) => (
  <Svg {...props}>
    <path d="M4.5 7h15" />
    <path d="M9 7V5.8A1.8 1.8 0 0 1 10.8 4h2.4A1.8 1.8 0 0 1 15 5.8V7" />
    <path d="M7.5 7l.7 10.2A1.8 1.8 0 0 0 10 19h4a1.8 1.8 0 0 0 1.8-1.8L16.5 7" />
    <path d="M10 10.5v5" />
    <path d="M14 10.5v5" />
  </Svg>
);

export const IconCpu = (props: IconProps) => (
  <Svg {...props}>
    <rect x="7" y="7" width="10" height="10" rx="2" />
    <path d="M10 3v3M14 3v3M10 18v3M14 18v3M3 10h3M3 14h3M18 10h3M18 14h3" />
  </Svg>
);

export const IconFolder = (props: IconProps) => (
  <Svg {...props}>
    <path d="M3.5 8.5A2.5 2.5 0 0 1 6 6h4l1.5 2H18a2.5 2.5 0 0 1 2.5 2.5V16A2.5 2.5 0 0 1 18 18.5H6A2.5 2.5 0 0 1 3.5 16V8.5Z" />
  </Svg>
);

export const IconMessage = (props: IconProps) => (
  <Svg {...props}>
    <path d="M5 6.5h14a2.5 2.5 0 0 1 2.5 2.5v5a2.5 2.5 0 0 1-2.5 2.5H11l-4.5 3v-3H5A2.5 2.5 0 0 1 2.5 14V9A2.5 2.5 0 0 1 5 6.5Z" />
  </Svg>
);

export const IconCode = (props: IconProps) => (
  <Svg {...props}>
    <path d="M9 8.5 5.5 12 9 15.5" />
    <path d="M15 8.5 18.5 12 15 15.5" />
    <path d="M13 7 11 17" />
  </Svg>
);

export const IconCalendar = (props: IconProps) => (
  <Svg {...props}>
    <rect x="4" y="6" width="16" height="14" rx="2" />
    <path d="M8 4v4M16 4v4M4 10h16" />
  </Svg>
);

export const IconStar = (props: IconProps) => (
  <Svg {...props}>
    <path d="M12 4.2l2.3 4.7 5.2.8-3.8 3.7.9 5.2L12 16.2l-4.6 2.4.9-5.2-3.8-3.7 5.2-.8L12 4.2Z" />
  </Svg>
);
