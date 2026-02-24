import React from 'react';
import { Phase, Role } from '../types';
import { PHASE_COLORS } from '../constants';

interface RadialProgressProps {
  currentPhase: Phase;
  onPhaseSelect: (phase: Phase) => void;
  picoCompleteness: number; // For ASK phase visualization
  patientContext: string;
  userRole: Role;
  onCenterClick: () => void;
}

const phases = Object.values(Phase);
const CENTER = 300;
const RADIUS = 200;
const INNER_RADIUS = 120;

// Helper to calculate SVG path for a sector
const getSectorPath = (index: number, total: number) => {
  const startAngle = (index * 360) / total - 90; // -90 to start at top
  const endAngle = ((index + 1) * 360) / total - 90;

  const toRad = (deg: number) => (deg * Math.PI) / 180;

  const x1 = CENTER + RADIUS * Math.cos(toRad(startAngle));
  const y1 = CENTER + RADIUS * Math.sin(toRad(startAngle));
  const x2 = CENTER + RADIUS * Math.cos(toRad(endAngle));
  const y2 = CENTER + RADIUS * Math.sin(toRad(endAngle));

  const x3 = CENTER + INNER_RADIUS * Math.cos(toRad(endAngle));
  const y3 = CENTER + INNER_RADIUS * Math.sin(toRad(endAngle));
  const x4 = CENTER + INNER_RADIUS * Math.cos(toRad(startAngle));
  const y4 = CENTER + INNER_RADIUS * Math.sin(toRad(startAngle));

  return `M ${x1} ${y1} A ${RADIUS} ${RADIUS} 0 0 1 ${x2} ${y2} L ${x3} ${y3} A ${INNER_RADIUS} ${INNER_RADIUS} 0 0 0 ${x4} ${y4} Z`;
};

const RadialProgress: React.FC<RadialProgressProps> = ({ 
  currentPhase, 
  onPhaseSelect, 
  picoCompleteness,
  patientContext,
  userRole,
  onCenterClick
}) => {
  return (
    <div className="relative w-full h-full flex items-center justify-center">
      <svg width="600" height="600" viewBox="0 0 600 600" className="w-[500px] h-[500px] md:w-[600px] md:h-[600px] transition-all duration-500">
        <defs>
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          <radialGradient id="centerGlass" cx="35%" cy="30%" r="65%" fx="30%" fy="25%">
            <stop offset="0%" stopColor="var(--color-glass-highlight)" stopOpacity="0.9" />
            <stop offset="40%" stopColor="var(--color-bg-secondary)" stopOpacity="0.6" />
            <stop offset="100%" stopColor="var(--color-bg-tertiary)" stopOpacity="0.3" />
          </radialGradient>
          <linearGradient id="centerSheen" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--color-glass-sheen)" stopOpacity="0.8" />
            <stop offset="50%" stopColor="var(--color-glass-sheen)" stopOpacity="0.2" />
            <stop offset="100%" stopColor="var(--color-glass-sheen)" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Sectors */}
        {phases.map((phase, index) => {
          const isActive = phase === currentPhase;
          const color = PHASE_COLORS[phase];
          
          return (
            <g 
              key={phase} 
              onClick={() => onPhaseSelect(phase)}
              className="cursor-pointer transition-all duration-300 hover:opacity-90 group"
            >
              <path
                d={getSectorPath(index, phases.length)}
                fill={color}
                opacity={isActive ? 1 : 0.3}
                stroke={isActive ? '#fff' : 'none'}
                strokeWidth={isActive ? 3 : 1}
                strokeOpacity={isActive ? 1 : 0.1}
                filter={isActive ? 'url(#glow)' : ''}
                className="transition-all duration-500 ease-out"
              />
              
              {/* Label inside sector */}
              <text
                x={CENTER + (RADIUS + INNER_RADIUS) / 2 * Math.cos(((index * 360 / 5 + 36) - 90) * Math.PI / 180)}
                y={CENTER + (RADIUS + INNER_RADIUS) / 2 * Math.sin(((index * 360 / 5 + 36) - 90) * Math.PI / 180)}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="var(--color-text-primary)"
                className={`font-bold tracking-wider pointer-events-none drop-shadow-sm ${isActive ? 'text-lg' : 'text-xs opacity-80'}`}
                style={{ 
                    transformBox: 'fill-box', 
                    transformOrigin: 'center', 
                }}
              >
                {phase}
              </text>
            </g>
          );
        })}

        {/* Center Hub - Clickable */}
        <g 
            onClick={onCenterClick} 
            className="cursor-pointer hover:opacity-90 transition-opacity"
        >
            {/* Outer ring of hub */}
            <circle 
                cx={CENTER} 
                cy={CENTER} 
                r={INNER_RADIUS - 5} 
                fill="url(#centerGlass)" 
                stroke={PHASE_COLORS[currentPhase]}
                strokeWidth="2"
                className="drop-shadow-xl transition-colors duration-500" 
            />
            <circle
                cx={CENTER}
                cy={CENTER}
                r={INNER_RADIUS - 10}
                fill="url(#centerSheen)"
                stroke="rgba(255,255,255,0.3)"
                strokeWidth="1"
                className="transition-opacity duration-500"
            />
            <circle
                cx={CENTER}
                cy={CENTER}
                r={INNER_RADIUS - 20}
                fill="none"
                stroke="var(--color-border)"
                strokeWidth="1"
            />
            
            <foreignObject x={CENTER - 80} y={CENTER - 80} width="160" height="160">
              <div className="w-full h-full flex flex-col items-center justify-center text-center select-none theme-transition">
                
                {/* Patient Section */}
                <div className="mb-3">
                    <div className="text-[10px] uppercase tracking-widest font-bold opacity-80" style={{ color: 'var(--color-text-secondary)' }}>Patient</div>
                    <div className="text-lg font-bold truncate max-w-[140px]" title={patientContext} style={{ color: 'var(--color-text-primary)' }}>
                        {patientContext || "New Patient"}
                    </div>
                </div>

                <div className="w-12 h-[1px] mb-3 opacity-20" style={{ backgroundColor: 'var(--color-text-primary)' }}></div>

                {/* Role Section */}
                <div>
                    <div className="text-[10px] uppercase tracking-widest font-bold opacity-80" style={{ color: 'var(--color-text-secondary)' }}>Role</div>
                    <div className="text-sm font-medium text-sky-500 truncate max-w-[140px]">
                        {userRole}
                    </div>
                </div>

                <div className="absolute bottom-2 opacity-0 hover:opacity-100 transition-opacity text-[10px]" style={{ color: 'var(--color-text-muted)' }}>
                    Click to Edit
                </div>

              </div>
            </foreignObject>
        </g>
      </svg>
    </div>
  );
};

export default RadialProgress;
