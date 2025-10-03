import vueCssModule from "vite-plugin-vue-css-module"

export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },

  modules: [
    "nuxt-proxy",
  ],

  vite: {
    plugins: [
      vueCssModule({ attrName: "mclass", pugClassLiterals: true }),
    ],
    css: {
      preprocessorOptions: {
        scss: {
          additionalData: "@use '@/styles/mixins' as *;",
          api: "modern",
        },
      },
    },
  },

  proxy: {
    options: {
      target: "http://backend:3277", // твой Flask API
      changeOrigin: true,
      pathFilter: [
        "/api",
      ],
      pathRewrite: {
        "^/api": "", // убираем /api перед отправкой на Flask
      },
    },
  },
})
