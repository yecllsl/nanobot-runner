import { NavLink } from 'react-router-dom';

const navItems = [
  { path: '/', label: '仪表盘', icon: '📊' },
  { path: '/vdot', label: 'VDOT', icon: '📈' },
  { path: '/training-load', label: '负荷', icon: '💪' },
  { path: '/activities', label: '活动', icon: '🏃' },
  { path: '/import', label: '导入', icon: '📥' },
  { path: '/body-signals', label: '身体', icon: '❤️' },
  { path: '/plan', label: '计划', icon: '📋' },
  { path: '/evolution', label: '进化', icon: '🧬' },
  { path: '/settings', label: '设置', icon: '⚙️' },
];

export default function Sidebar() {
  return (
    <aside className="w-16 lg:w-48 bg-white border-r border-gray-200 flex flex-col py-4 shrink-0">
      <nav className="flex-1 space-y-1 px-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`
            }
          >
            <span className="text-lg">{item.icon}</span>
            <span className="hidden lg:inline">{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
