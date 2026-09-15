/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/renderer/**/*.{js,jsx,ts,tsx}",
    "./src/renderer/index.html"
  ],
  theme: {
    extend: {
      // Cyberpunk Color Palette
      colors: {
        'deep-space-black': '#111315',
        'night-blue': '#1B1F24',
        'industrial-steel-blue': '#5B6773',
        'neon-magenta': '#F97316',
        'titanium-white': '#F5F7FA',
        // Semantic color aliases for easier usage
        'cyberpunk': {
          'bg-primary': '#111315',
          'bg-secondary': '#1B1F24',
          'bg-tertiary': '#5B6773',
          'accent': '#F97316',
          'text': '#F5F7FA',
        }
      },
      // Typography System - Technical Monospace Fonts
      fontFamily: {
        'mono': ['JetBrains Mono', 'Roboto Mono', 'Consolas', 'Monaco', 'monospace'],
        'display': ['JetBrains Mono', 'Roboto Mono', 'monospace'],
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'base': ['1rem', { lineHeight: '1.5rem' }],
        'lg': ['1.125rem', { lineHeight: '1.75rem' }],
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
      },
      // Sharp Edges - Max 4px Border Radius
      borderRadius: {
        'none': '0',
        'sm': '2px',
        'DEFAULT': '4px',
        'md': '4px',
        'lg': '4px',
        'cyberpunk': '4px',
      },
      // Custom Animations
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite alternate',
        'pulse-border': 'pulse-border 2s ease-in-out infinite',
        'electric-arc': 'electric-arc 0.3s ease-out',
        'vertical-gradient': 'vertical-gradient 3s ease-in-out infinite',
        'glow-pulse': 'glow-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'scan-line': 'scan-line 4s linear infinite',
      },
      // Keyframe Animations
      keyframes: {
        'pulse-glow': {
          '0%': { 
            boxShadow: '0 0 5px #E94560, 0 0 10px #E94560, 0 0 15px #E94560'
          },
          '100%': { 
            boxShadow: '0 0 10px #E94560, 0 0 20px #E94560, 0 0 30px #E94560, 0 0 40px #E94560'
          }
        },
        'pulse-border': {
          '0%, 100%': { 
            borderColor: '#0F3460',
            boxShadow: '0 0 0 0 rgba(233, 69, 96, 0)'
          },
          '50%': { 
            borderColor: '#E94560',
            boxShadow: '0 0 0 4px rgba(233, 69, 96, 0.3)'
          }
        },
        'electric-arc': {
          '0%': { 
            opacity: '0', 
            transform: 'scale(0.8)',
            filter: 'brightness(1)'
          },
          '50%': { 
            opacity: '1', 
            transform: 'scale(1.1)',
            filter: 'brightness(1.5)'
          },
          '100%': { 
            opacity: '0', 
            transform: 'scale(1)',
            filter: 'brightness(1)'
          }
        },
        'vertical-gradient': {
          '0%, 100%': { 
            backgroundPosition: '0% 0%',
            backgroundSize: '100% 200%'
          },
          '50%': { 
            backgroundPosition: '0% 100%',
            backgroundSize: '100% 200%'
          }
        },
        'glow-pulse': {
          '0%, 100%': {
            opacity: '1',
            filter: 'drop-shadow(0 0 2px #E94560) drop-shadow(0 0 4px #E94560)'
          },
          '50%': {
            opacity: '0.8',
            filter: 'drop-shadow(0 0 4px #E94560) drop-shadow(0 0 8px #E94560) drop-shadow(0 0 12px #E94560)'
          }
        },
        'scan-line': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' }
        }
      },
      // Box Shadow for Glow Effects
      boxShadow: {
        'glow-sm': '0 0 5px #E94560',
        'glow': '0 0 10px #E94560, 0 0 20px #E94560',
        'glow-lg': '0 0 15px #E94560, 0 0 30px #E94560, 0 0 45px #E94560',
        'glow-xl': '0 0 20px #E94560, 0 0 40px #E94560, 0 0 60px #E94560, 0 0 80px #E94560',
        'inner-glow': 'inset 0 0 10px #E94560',
        'steel': '0 2px 4px rgba(15, 52, 96, 0.3)',
      },
      // Background Images for Gradients
      backgroundImage: {
        'gradient-vertical': 'linear-gradient(180deg, #1A1A2E 0%, #0D0D0D 100%)',
        'gradient-radial': 'radial-gradient(circle, #1A1A2E 0%, #0D0D0D 100%)',
        'gradient-cyberpunk': 'linear-gradient(135deg, #0F3460 0%, #1A1A2E 50%, #0D0D0D 100%)',
      },
      // Spacing for Heavy Negative Space
      spacing: {
        '18': '4.5rem',
        '22': '5.5rem',
        '26': '6.5rem',
        '30': '7.5rem',
      }
    },
  },
  plugins: [
    // Cyberpunk Theme Plugin
    require('./src/renderer/styles/cyberpunk-plugin.js')
  ],
}
