import clsx from "clsx";

export interface TabDefinition {
  key: string;
  label: string;
}

interface ReportTabsProps {
  tabs: TabDefinition[];
  activeTab: string;
  onTabChange: (key: string) => void;
}

export function ReportTabs({ tabs, activeTab, onTabChange }: ReportTabsProps) {
  return (
    <div className="flex gap-1 border-b border-dark-border">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onTabChange(tab.key)}
          className={clsx(
            "px-4 py-2.5 text-sm font-medium transition-colors border-b-2",
            activeTab === tab.key
              ? "text-accent-secondary border-accent-primary"
              : "text-gray-500 border-transparent hover:text-gray-300",
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
