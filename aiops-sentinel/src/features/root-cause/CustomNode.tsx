import { Handle, Position } from '@xyflow/react';

export function CustomNode({ data }: { data: Record<string, any> }) {
  const isError = data.status === 'error';
  const isWarning = data.status === 'warning';
  
  const bgColor = isError ? 'bg-error text-on-error' : isWarning ? 'bg-tertiary-container text-on-tertiary' : 'bg-secondary-container text-on-secondary';
  // const ringColor = isError ? 'ring-error/80' : isWarning ? 'ring-tertiary-container/80' : 'ring-secondary-container/80';
  const icon = isError ? 'error' : isWarning ? 'warning' : 'check_circle';

  return (
    <div className={`relative flex flex-col items-center group transition-transform hover:scale-110`}>
      <Handle type="target" position={Position.Top} className="opacity-0" />
      
      {isError && (
        <div className="absolute -top-7 whitespace-nowrap px-2 py-0.5 rounded-DEFAULT bg-error text-on-error font-label-code-sm text-[0.625rem] font-bold shadow-lg flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-surface-container-lowest animate-ping"></span>
          ROOT CAUSE (94%)
        </div>
      )}

      {isError && (
        <>
          <div className="absolute -inset-4 rounded-full bg-error/20 animate-ping pointer-events-none"></div>
          <div className={`absolute -inset-2 rounded-full border border-error/80 animate-pulse pointer-events-none`}></div>
        </>
      )}
      
      <div className={`w-12 h-12 rounded-full flex items-center justify-center shadow-md z-10 ${bgColor} ${isError ? 'border-2 border-white/80' : ''}`}>
        <span className="material-symbols-outlined text-[24px]">{icon}</span>
      </div>

      <div className="absolute top-14 text-center whitespace-nowrap">
        <span className={`font-label-code-md font-bold text-[0.75rem] ${isError ? 'text-error drop-shadow-md' : 'text-on-surface'}`}>{data.label}</span>
      </div>
      
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
    </div>
  );
}
