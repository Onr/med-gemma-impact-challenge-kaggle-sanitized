import React, { useState, useEffect } from 'react';
import { Role } from '../types';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentRole: Role;
  currentPatientContext: string;
  onSave: (role: Role, context: string) => void;
}

const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  currentRole,
  currentPatientContext,
  onSave
}) => {
  const [role, setRole] = useState<Role>(currentRole);
  const [context, setContext] = useState(currentPatientContext);

  useEffect(() => {
    if (isOpen) {
      setRole(currentRole);
      setContext(currentPatientContext);
    }
  }, [isOpen, currentRole, currentPatientContext]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="border rounded-2xl w-full max-w-md shadow-2xl overflow-hidden transform transition-all scale-100 theme-transition" style={{ backgroundColor: 'var(--color-modal-bg)', borderColor: 'var(--color-border)' }}>
        <div className="p-6">
          <h3 className="text-xl font-bold mb-1" style={{ color: 'var(--color-text-primary)' }}>Session Settings</h3>
          <p className="text-sm mb-6 opacity-60" style={{ color: 'var(--color-text-secondary)' }}>Configure the current clinical context.</p>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider mb-2 opacity-60" style={{ color: 'var(--color-text-secondary)' }}>User Role</label>
              <div className="grid grid-cols-2 gap-2">
                {Object.values(Role).map((r) => (
                  <button
                    key={r}
                    onClick={() => setRole(r)}
                    className={`p-2 text-xs rounded-lg border transition-colors text-left truncate theme-transition ${role === r
                        ? 'bg-sky-600 border-sky-500 text-white'
                        : 'hover:opacity-80'
                      }`}
                    style={role === r ? {} : { backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider mb-2 opacity-60" style={{ color: 'var(--color-text-secondary)' }}>Patient ID</label>
              <input
                type="text"
                value={context}
                onChange={(e) => setContext(e.target.value)}
                placeholder="E.g., PT-014"
                className="w-full border rounded-lg p-3 text-sm focus:outline-none focus:border-sky-500 theme-transition"
                style={{ backgroundColor: 'var(--color-bg-input)', borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
              />
            </div>
          </div>
        </div>

        <div className="p-4 border-t flex justify-end gap-3" style={{ backgroundColor: 'var(--color-bg-tertiary)', borderColor: 'var(--color-border)' }}>
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm opacity-60 hover:opacity-100 transition-colors"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            Cancel
          </button>
          <button
            onClick={() => { onSave(role, context); onClose(); }}
            className="px-6 py-2 bg-sky-600 hover:bg-sky-500 text-white text-sm font-semibold rounded-lg shadow-lg shadow-sky-900/20 transition-all"
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
