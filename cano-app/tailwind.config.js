/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,jsx,ts,tsx}",
    "./components/**/*.{js,jsx,ts,tsx}",
  ],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        // Colores personalizados del tema
        primary: '#3B82F6', // Azul
        'primary-dark': '#1E40AF', // Azul oscuro
        'primary-light': '#DBEAFE', // Azul claro
        bg: '#FFFFFF', // Blanco
        'bg-secondary': '#F8FAFC', // Gris muy claro
        'bg-tertiary': '#E2E8F0', // Gris claro
        border: '#E2E8F0', // Gris para bordes
        text: '#1E293B', // Gris oscuro (texto)
        'text-secondary': '#64748B', // Gris medio (texto secundario)
      },
    },
  },
  plugins: [],
}