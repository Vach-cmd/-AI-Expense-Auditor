import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  FileText, 
  Upload, 
  BarChart3, 
  Settings,
  Shield
} from 'lucide-react';
import { useAuthStore } from '../stores/authStore';

const Sidebar: React.FC = () => {
  const { user } = useAuthStore();

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, permission: 'read' },
    { name: 'Invoices', href: '/invoices', icon: FileText, permission: 'read' },
    { name: 'Upload', href: '/upload', icon: Upload, permission: 'write' },
    { name: 'Analytics', href: '/analytics', icon: BarChart3, permission: 'audit' },
    { name: 'Admin', href: '/admin', icon: Settings, permission: 'admin' },
  ];

  const filteredNavigation = navigation.filter(item => {
    if (!user) return false;
    
    const rolePermissions = {
      'admin': ['read', 'write', 'delete', 'admin', 'audit', 'approve'],
      'auditor': ['read', 'write', 'audit'],
      'manager': ['read', 'write', 'approve'],
      'user': ['read', 'write']
    };
    
    return rolePermissions[user.role as keyof typeof rolePermissions]?.includes(item.permission);
  });

  return (
    <div className="w-64 bg-white shadow-sm border-r border-gray-200 min-h-screen">
      <nav className="mt-6 px-3">
        <div className="space-y-1">
          {filteredNavigation.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.href}
                className={({ isActive }) =>
                  `group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    isActive
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`
                }
              >
                <Icon
                  className="mr-3 h-5 w-5 flex-shrink-0"
                  aria-hidden="true"
                />
                {item.name}
              </NavLink>
            );
          })}
        </div>
      </nav>
    </div>
  );
};

export default Sidebar;
