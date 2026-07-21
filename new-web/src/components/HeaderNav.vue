<script setup lang="ts">
import HeaderTheme from './HeaderTheme.vue'
import HeaderLogin from './HeaderLogin.vue'
</script>

<template>
  <div class="header-nav">
    <div class="header-tool">
      <HeaderTheme />
      <HeaderLogin />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.header-nav {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  flex: 1;
  height: 100%;
  overflow: hidden;
}

.header-tool {
  display: flex;
  align-items: center;
  height: 100%;
}
</style>
