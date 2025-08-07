<template>
  <div id="app">
    <nav style="padding: 1rem; background: #f0f0f0;">
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