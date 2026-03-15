import SettingsSkeleton from './SettingsSkeleton';

export default function SettingsLoading() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(214,181,136,0.18),transparent_22%),radial-gradient(circle_at_top_right,rgba(210,223,214,0.25),transparent_26%),linear-gradient(180deg,#faf7f2_0%,#f5f2ec_52%,#f2efe8_100%)]">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.72),transparent_62%)]"
        aria-hidden
      />
      <div className="relative mx-auto max-w-3xl space-y-8 px-4 py-6 pb-24 sm:px-6 lg:px-8 md:space-y-10">
        <SettingsSkeleton />
      </div>
    </div>
  );
}
