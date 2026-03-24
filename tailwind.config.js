/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./my_app/templates/**/*.html",
    "./theme/templates/**/*.html",
    "./assets/css/styles.css",    // ← include your CSS file!
    "./my_app/static/js/**/*.js'"
  ],
  safelist: [
    // all of the atomic classes you @apply in styles.css:
    'px-4', 'py-2', 'rounded-md',
    'border', 'border-[#D1D5DB]',
    'bg-[#FFFFFF]', 'text-[#1F2937]',
    'hover:bg-[#F3F4F6]', 'focus:ring-2', 'focus:ring-[#BFDBFE]',
    'bg-[#2563EB]', 'text-[#FFFFFF]', 'border-transparent',
  ],
  theme: { extend: {} },
  plugins: [],
}
