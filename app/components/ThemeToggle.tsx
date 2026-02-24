
import React from 'react';

interface ThemeToggleProps {
    isDark: boolean;
    onToggle: () => void;
    className?: string;
}

const ThemeToggle: React.FC<ThemeToggleProps> = ({ isDark, onToggle, className = '' }) => {
    return (
        <button
            onClick={onToggle}
            className={`theme-toggle ${className}`}
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
            <span className="material-symbols-outlined text-xl transition-transform duration-300">
                {isDark ? 'light_mode' : 'dark_mode'}
            </span>
        </button>
    );
};

export default ThemeToggle;
