<script setup lang="ts">
import { OIcon } from '@opensig/opendesign'

const goLogin = () => {
  const origin = import.meta.env.VITE_LOGIN_ORIGIN || 'https://id.openeuler.openatom.cn'
  const url = `${origin}/login?redirect_uri=${encodeURIComponent(location.href)}&lang=zh`
  window.location.href = url
}
</script>

<template>
  <div class="opt-user">
    <div class="login" @click="goLogin">
      <OIcon class="icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path opacity="0.8" fill="currentColor" d="M7.058 7.747c0 1.643 0.802 3.099 2.035 3.997-3.646 1.185-6.278 4.539-6.278 8.497 0 0.387 0.313 0.7 0.7 0.7s0.7-0.313 0.7-0.7c0-4.127 3.412-7.487 7.655-7.554 0.043 0.001 0.086 0.002 0.129 0.002 2.73 0 4.942-2.213 4.942-4.942s-2.213-4.942-4.942-4.942c-2.73 0-4.942 2.213-4.942 4.942zM12.058 11.289c-0.019-0.002-0.038-0.002-0.058-0.002-0.040 0-0.081 0-0.121 0.001-1.9-0.064-3.421-1.625-3.421-3.54 0-1.956 1.586-3.542 3.542-3.542s3.542 1.586 3.542 3.542c0 1.937-1.555 3.511-3.484 3.542zM16.337 12.346c2.958 1.548 4.847 4.558 4.847 7.896 0 0.387-0.313 0.7-0.7 0.7s-0.7-0.313-0.7-0.7c0-2.808-1.592-5.345-4.096-6.655-0.343-0.179-0.475-0.602-0.296-0.945s0.602-0.475 0.945-0.296z"></path>
        </svg>
      </OIcon>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.opt-user {
  height: 100%;
  display: flex;
  align-items: center;
  position: relative;
  margin-left: var(--o-gap-5);

  @include respond-to('<=pad_v') {
    margin-left: var(--o-gap-2);
  }
}

.login {
  height: 24px;
  .icon {
    font-size: var(--o-icon_size-m);
    cursor: pointer;
    color: var(--o-color-info1);

    &:hover {
      color: var(--o-color-primary1);
    }
  }
}
</style>
