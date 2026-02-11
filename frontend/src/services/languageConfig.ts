/**
 * 语言配置服务
 * 管理用户的语言偏好设置
 */

export type LanguageCode = 'zh-CN' | 'en-US' | 'ja-JP' | 'ko-KR' | 'fr-FR' | 'de-DE' | 'es-ES' | 'auto';

export interface LanguageOption {
  code: LanguageCode;
  label: string;
  icon: string;
  systemPrompt: string;
}

const STORAGE_KEY = 'ai_chat_language';

export const LANGUAGE_OPTIONS: LanguageOption[] = [
  {
    code: 'auto',
    label: '自动检测',
    icon: '🌐',
    systemPrompt: 'You can respond in any language that matches the user\'s input language.',
  },
  {
    code: 'zh-CN',
    label: '简体中文',
    icon: '🇨🇳',
    systemPrompt: '请使用简体中文回答所有问题。无论用户使用什么语言提问，你都必须用简体中文回复。',
  },
  {
    code: 'en-US',
    label: 'English',
    icon: '🇺🇸',
    systemPrompt: 'Please answer all questions in English. No matter what language the user uses, you must reply in English.',
  },
  {
    code: 'ja-JP',
    label: '日本語',
    icon: '🇯🇵',
    systemPrompt: 'すべての質問に日本語で答えてください。ユーザーがどの言語を使用しても、日本語で返信する必要があります。',
  },
  {
    code: 'ko-KR',
    label: '한국어',
    icon: '🇰🇷',
    systemPrompt: '모든 질문에 한국어로 답변해 주세요. 사용자가 어떤 언어를 사용하든 한국어로 답변해야 합니다.',
  },
  {
    code: 'fr-FR',
    label: 'Français',
    icon: '🇫🇷',
    systemPrompt: 'Veuillez répondre à toutes les questions en français. Quelle que soit la langue utilisée par l\'utilisateur, vous devez répondre en français.',
  },
  {
    code: 'de-DE',
    label: 'Deutsch',
    icon: '🇩🇪',
    systemPrompt: 'Bitte beantworten Sie alle Fragen auf Deutsch. Unabhängig davon, welche Sprache der Benutzer verwendet, müssen Sie auf Deutsch antworten.',
  },
  {
    code: 'es-ES',
    label: 'Español',
    icon: '🇪🇸',
    systemPrompt: 'Por favor, responde a todas las preguntas en español. No importa qué idioma use el usuario, debes responder en español.',
  },
];

class LanguageConfigService {
  /**
   * 获取当前语言设置
   */
  getLanguage(): LanguageCode {
    const saved = localStorage.getItem(STORAGE_KEY);
    return (saved as LanguageCode) || 'auto';
  }

  /**
   * 设置语言
   */
  setLanguage(language: LanguageCode): void {
    localStorage.setItem(STORAGE_KEY, language);
  }

  /**
   * 获取语言的 system prompt
   */
  getSystemPrompt(language?: LanguageCode): string {
    const lang = language || this.getLanguage();
    const option = LANGUAGE_OPTIONS.find(opt => opt.code === lang);
    return option?.systemPrompt || LANGUAGE_OPTIONS[0].systemPrompt;
  }

  /**
   * 获取语言选项信息
   */
  getLanguageOption(language?: LanguageCode): LanguageOption | undefined {
    const lang = language || this.getLanguage();
    return LANGUAGE_OPTIONS.find(opt => opt.code === lang);
  }

  /**
   * 获取所有语言选项
   */
  getAllLanguages(): LanguageOption[] {
    return LANGUAGE_OPTIONS;
  }
}

export const languageConfigService = new LanguageConfigService();
