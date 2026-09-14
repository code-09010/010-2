<template>
  <div class="page">
    <header class="topbar">
      <router-link to="/" class="brand">🔥 烧窑记录</router-link>
      <nav class="topnav">
        <router-link to="/">窑次</router-link>
        <router-link to="/kilns">窑炉档案</router-link>
      </nav>
      <span class="tagline">窑次 · 窑位 · 曲线 · 看火 · 开窑</span>
    </header>
    <main>
      <router-view />
    </main>
  </div>
</template>
