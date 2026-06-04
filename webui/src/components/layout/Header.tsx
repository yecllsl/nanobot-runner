import { AGENT_CHAT_URL } from '../../utils/constants';

export default function Header() {
  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4 lg:px-6 shrink-0">
      <h1 className="text-lg font-bold text-gray-900">Nanobot Runner</h1>
      <div className="flex items-center gap-4">
        <a
          href={AGENT_CHAT_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-primary-600 hover:text-primary-700 font-medium"
        >
          Agent对话 →
        </a>
      </div>
    </header>
  );
}
