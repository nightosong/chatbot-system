import React, { useEffect, useMemo, useState } from 'react';

type PlatformBadgeProps = {
  platform: string;
  className?: string;
  size?: number;
};

const normalizePlatform = (platform: string): string => {
  if (platform === 'skywork_router') return 'skywork';
  return platform.toLowerCase();
};

const OFFICIAL_ICON_SLUGS: Record<string, string> = {
  openai: 'openai',
  gemini: 'gemini-color',
  qwen: 'qwen-color',
  claude: 'claude-color',
};

const CUSTOM_OFFICIAL_ICON_URLS: Record<string, string> = {
  kimi: 'https://statics.moonshot.cn/kimi-chat/favicon.ico',
  deepseek: 'https://deepseek.com/favicon.ico',
  doubao: 'https://lf-flow-web-cdn.doubao.com/obj/flow-doubao/doubao/web/logo-icon.png',
};

const getOfficialIconUrl = (slug: string): string =>
  `https://registry.npmmirror.com/@lobehub/icons-static-svg/latest/files/icons/${slug}.svg`;

const SkyworkOfficialIcon: React.FC<{ size: number }> = ({ size }) => (
  <svg
    className="platform-badge-image platform-badge-image-skywork"
    width={size}
    height={size}
    viewBox="-1.5 0 31 28"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path
      d="M16.0245 2.09232C12.2957 -0.817388 6.90394 -0.720343 3.27379 2.55946C-0.795527 6.23401 -1.11463 12.5107 2.55993 16.5784C5.83973 20.2102 11.1937 20.8533 15.1988 18.3367L7.4895 9.80166L16.0245 2.09232Z"
      fill="#4D5EFF"
    />
    <path
      d="M12.6052 25.9071C16.334 28.8168 21.7258 28.7197 25.3559 25.4399C29.4236 21.7654 29.7427 15.4887 26.0681 11.421C22.7883 7.78923 17.4344 7.1461 13.4292 9.6627L21.1386 18.1977L12.6035 25.9071H12.6052Z"
      fill="#00FFCE"
    />
  </svg>
);

const PlatformGlyph: React.FC<{ platform: string }> = ({ platform }) => {
  switch (platform) {
    case 'openai':
      return (
        <>
          <circle cx="12" cy="12" r="3.2" />
          <path d="M12 4.2 15 6l.2 3.5L12 11.2 8.8 9.5 9 6 12 4.2Z" />
          <path d="M4.2 12 6 9l3.5-.2L11.2 12 9.5 15 6 14.8 4.2 12Z" />
          <path d="M12 19.8 9 18l-.2-3.5 3.2-1.7 3.2 1.7L15 18l-3 1.8Z" />
          <path d="M19.8 12 18 15l-3.5.2-1.7-3.2 1.7-3.2L18 9l1.8 3Z" />
        </>
      );
    case 'gemini':
      return (
        <path d="M12 3.8 14.2 9.8 20.2 12l-6 2.2-2.2 6-2.2-6-6-2.2 6-2.2L12 3.8Z" />
      );
    case 'skywork':
      return (
        <>
          <circle cx="7.5" cy="7.5" r="1.8" fill="currentColor" stroke="none" />
          <circle cx="16.5" cy="7.5" r="1.8" fill="currentColor" stroke="none" />
          <circle cx="12" cy="16.5" r="1.8" fill="currentColor" stroke="none" />
          <path d="M9 8.8 11 14M15 8.8 13 14M9.2 7.5h5.6" />
        </>
      );
    case 'kimi':
      return (
        <>
          <path d="M14.8 5.2A7.1 7.1 0 1 0 14.8 18.8 5.7 5.7 0 1 1 14.8 5.2Z" />
          <circle cx="16.5" cy="8.2" r="0.9" fill="currentColor" stroke="none" />
        </>
      );
    case 'qwen':
      return (
        <>
          <path d="M6 12c0-3.2 2.4-5.8 5.5-5.8 2.5 0 4.2 1.2 5.2 3" />
          <path d="M18 12c0 3.2-2.4 5.8-5.5 5.8-2.5 0-4.2-1.2-5.2-3" />
        </>
      );
    case 'deepseek':
      return (
        <>
          <path d="M12 4.5 18.5 12 12 19.5 5.5 12 12 4.5Z" />
          <path d="M12 8.2V15.8M8.6 12h6.8" />
        </>
      );
    case 'claude':
      return (
        <>
          <path d="M16.6 7.8A5.4 5.4 0 1 0 16.6 16.2" />
          <path d="M12.4 8.7h4.1M12.4 15.3h4.1" />
        </>
      );
    case 'doubao':
      return (
        <>
          <path d="M6 7.5h12a2.5 2.5 0 0 1 2.5 2.5v4a2.5 2.5 0 0 1-2.5 2.5H12l-3.6 2.5v-2.5H6A2.5 2.5 0 0 1 3.5 14v-4A2.5 2.5 0 0 1 6 7.5Z" />
          <circle cx="9" cy="12" r="0.9" fill="currentColor" stroke="none" />
          <circle cx="12" cy="12" r="0.9" fill="currentColor" stroke="none" />
          <circle cx="15" cy="12" r="0.9" fill="currentColor" stroke="none" />
        </>
      );
    default:
      return (
        <>
          <circle cx="12" cy="12" r="8" />
          <path d="M12 8v8M8 12h8" />
        </>
      );
  }
};

export const PlatformBadge: React.FC<PlatformBadgeProps> = ({
  platform,
  className = '',
  size = 30,
}) => {
  const normalizedPlatform = normalizePlatform(platform);
  const [officialIconLoadFailed, setOfficialIconLoadFailed] = useState(false);
  const hasCustomOfficialIcon = normalizedPlatform === 'skywork';
  const customOfficialIcon = hasCustomOfficialIcon ? <SkyworkOfficialIcon size={size} /> : null;
  const customOfficialImageUrl = CUSTOM_OFFICIAL_ICON_URLS[normalizedPlatform] ?? null;

  const officialIconUrl = useMemo(() => {
    if (hasCustomOfficialIcon || customOfficialImageUrl) return null;
    const slug = OFFICIAL_ICON_SLUGS[normalizedPlatform];
    return slug ? getOfficialIconUrl(slug) : null;
  }, [hasCustomOfficialIcon, customOfficialImageUrl, normalizedPlatform]);

  useEffect(() => {
    setOfficialIconLoadFailed(false);
  }, [customOfficialImageUrl, officialIconUrl]);

  const useOfficialIcon = Boolean(customOfficialIcon || customOfficialImageUrl || officialIconUrl) && !officialIconLoadFailed;
  const combinedClassName =
    `platform-icon platform-badge platform-badge-${normalizedPlatform} ${useOfficialIcon ? 'has-official-icon' : ''} ${className}`.trim();
  const imageClassName =
    `platform-badge-image ${normalizedPlatform === 'doubao' ? 'platform-badge-image-doubao' : ''}`.trim();

  return (
    <span className={combinedClassName} aria-label={`${platform} model`}>
      {customOfficialIcon ? (
        customOfficialIcon
      ) : useOfficialIcon ? (
        <img
          className={imageClassName}
          src={customOfficialImageUrl ?? officialIconUrl!}
          alt={`${platform} logo`}
          width={size}
          height={size}
          loading="lazy"
          decoding="async"
          onError={() => setOfficialIconLoadFailed(true)}
        />
      ) : (
        <svg
          width={size}
          height={size}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <PlatformGlyph platform={normalizedPlatform} />
        </svg>
      )}
    </span>
  );
};

export default PlatformBadge;
