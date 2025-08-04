<!-- frontend/src/App.vue -->
<template>
  <div id="app">
    <nav>
      <router-link to="/">Список монет</router-link> |
      <router-link to="/admin">Админ</router-link>
    </nav>
    <router-view />
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}
nav {
  margin-bottom: 20px;
  padding: 10px;
  background: #f0f0f0;
  border-radius: 8px;
}
</style>