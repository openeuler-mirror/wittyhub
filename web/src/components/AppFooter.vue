<script setup lang="ts">
import { ODivider } from '@opensig/opendesign'
import ContentWrapper from './ContentWrapper.vue'

import LogoAtom from '@/assets/footer/atom-logo.png'
import LogoFooter from '@/assets/footer/footer-logo2.png'
import LogoFooterMo from '@/assets/footer/footer-logo1.png'
import policeIcon from '@/assets/footer/police.png'
import footerBg from '@/assets/footer/footer-bg.png'
import footerBgMo from '@/assets/footer/footer-bg-mo.png'
import CodeImgGzh from '@/assets/footer/img-gzh.png'
import CodeImgXzs from '@/assets/footer/img-xzs.png'
import CodeQrGzh from '@/assets/footer/code-zgz.jpg'
import CodeQrXzs from '@/assets/footer/code-xzs.png'

const footerCodeList = [
  { img: CodeImgGzh, code: CodeQrGzh, label: 'openEuler公众号' },
  { img: CodeImgXzs, code: CodeQrXzs, label: 'openEuler小助手' },
]

const quickNav = [
  {
    title: '关于 openEuler',
    list: [
      { title: '成员单位', link: '/zh/community/member/' },
      { title: '组织架构', link: '/zh/community/organization/' },
      { title: '社区章程', link: '/zh/community/charter/' },
      { title: '贡献看板', link: 'https://datastat.openeuler.org/zh/overview' },
      { title: '社区介绍', link: '/whitepaper/openEuler%20%E5%BC%80%E6%BA%90%E7%A4%BE%E5%8C%BA%E4%BB%8B%E7%BB%8D.pdf' },
    ],
  },
  {
    title: '新闻与资讯',
    list: [
      { title: '新闻', link: '/zh/interaction/news-list/' },
      { title: '博客', link: '/zh/interaction/blog-list/' },
      { title: '白皮书', link: '/zh/showcase/technical-white-paper/' },
    ],
  },
  {
    title: '获取与下载',
    list: [
      { title: '获取 openEuler 操作系统', link: '/zh/download/#get-openeuler' },
      { title: '最新社区发行版', link: '/zh/download/' },
      { title: '商业发行版', link: '/zh/download/commercial-release/' },
      { title: '软件中心', link: 'https://software.openeuler.org/zh' },
    ],
  },
  {
    title: '支持与服务',
    list: [
      { title: '文档', link: 'https://docs.openeuler.org/zh/' },
      { title: 'FAQ', link: 'https://www.openeuler.org/zh/faq/' },
      { title: '联系我们', link: '/zh/contact-us/' },
    ],
  },
  {
    title: '互动与交流',
    list: [
      { title: '邮件列表', link: '/zh/community/mailing-list/' },
      { title: '活动', link: '/zh/interaction/event-list/' },
      { title: '论坛', link: 'https://forum.openeuler.org/' },
    ],
  },
  {
    title: '贡献与成长',
    list: [
      { title: 'SIG 中心', link: '/zh/sig/sig-list/' },
      { title: '贡献攻略', link: '/zh/community/contribution/' },
      { title: '课程中心', link: '/zh/learn/mooc/' },
    ],
  },
]

const friendshipLinks = [
  { link: 'https://portal.mulanos.cn/', title: '木兰开源社区' },
  { link: 'https://www.hikunpeng.com/zh/', title: '鲲鹏社区' },
  { link: 'https://pcl.ac.cn/', title: '鹏城实验室' },
  { link: 'https://www.infoq.cn/?utm_source=openeuler&utm_medium=youlian', title: 'InfoQ' },
  { link: 'https://kaiyuanshe.cn/', title: '开源社' },
  { link: 'http://www.vulab.com.cn/', title: '中科微澜' },
  { link: 'https://www.authing.cn/', title: 'Authing' },
  { link: 'https://www.opengauss.org/zh/', title: 'openGauss' },
  { link: 'https://www.mindspore.cn/', title: '昇思MindSpore' },
  { link: 'https://www.openubmc.cn/', title: 'openUBMC' },
  { link: 'https://www.openfuyao.cn/', title: 'openFuyao' },
  { link: 'http://www.ebaina.com/', title: 'Ebaina' },
  { link: 'https://my.oschina.net/openeuler', title: '开源中国' },
  { link: 'https://blog.csdn.net/openEuler_', title: 'CSDN' },
  { link: 'https://gitee.com/openeuler', title: 'Gitee' },
  { link: 'https://space.bilibili.com/527064077', title: 'B站' },
  { link: 'https://juejin.cn/user/3183782863845454', title: '掘金' },
  { link: 'https://www.toutiao.com/c/user/token/MS4wLjABAAAAZivzVkJzMyQ44GzmX1i_ON0bgxL3E8ybHC-P9HMqZiqUgpYVnjCjynDt-SebKN7r', title: '头条' },
  { link: 'https://www.openeuler.org/zh/', title: 'openEuler 社区' },
]

const legalLinks = [
  { name: '品牌', url: 'https://www.openeuler.org/zh/other/brand/' },
  { name: '隐私声明', url: 'https://www.openeuler.org/zh/other/privacy/' },
  { name: '法律声明', url: 'https://www.openeuler.org/zh/other/legal/' },
  { name: '关于 cookies', url: 'https://www.openeuler.org/zh/other/cookies/' },
]
</script>

<template>
  <div class="footer">
    <ContentWrapper>
      <div class="atom">
        <p class="atom-text">
          openEuler 是由开放原子开源基金会孵化的全场景开源操作系统项目，面向数字基础设施四大核心场景（服务器、云计算、边缘计算、嵌入式），全面支持 ARM、x86、RISC-V、LoongArch、PowerPC、SW-64 等多样性计算架构
        </p>
        <a href="https://openatom.cn" target="_blank" rel="noopener noreferrer">
          <img :src="LogoAtom" class="atom-logo" alt="开放原子开源基金会" />
        </a>
      </div>
      <ODivider
        :style="{
          '--o-divider-bd-color': 'rgba(229, 229, 229, 0.12)',
          '--o-divider-gap': '16px',
        }"
      />
    </ContentWrapper>
    <div
      class="footer-content"
      :style="{
        '--footer-bg': `url(${footerBg})`,
        '--footer-bg-mo': `url(${footerBgMo})`,
      }"
    >
      <ContentWrapper>

        <div class="inner">
          <div class="footer-logo">
            <img class="show-pc" :src="LogoFooter" alt="openEuler" />
            <img class="show-mo" :src="LogoFooterMo" alt="openEuler" />
            <p>
              <a class="email" href="mailto:contact@openeuler.io" target="_blank" rel="noopener noreferrer">
                contact@openeuler.io
              </a>
            </p>
          </div>
          <div class="footer-option">
            <div class="footer-option-item">
              <template v-for="(link, index) in legalLinks" :key="link.name">
                <a :href="link.url" target="_blank" class="link" rel="noopener noreferrer">{{ link.name }}</a>
                <ODivider
                  v-if="index !== legalLinks.length - 1"
                  :style="{
                    '--o-divider-bd-color': 'var(--o-color-white)',
                    '--o-divider-label-gap': '0 8px',
                  }"
                  direction="v"
                />
              </template>
            </div>
            <p class="license"><span>遵循</span> 木兰宽松许可证第2版（MulanPSL2）</p>
            <div class="footer-info">
              <p class="copyright-text">版权所有 © {{ new Date().getFullYear() }} openEuler 保留一切权利</p>
              <div class="copyright">
                <a class="filing-link" href="https://beian.miit.gov.cn" target="_blank" rel="noopener noreferrer">
                  京ICP备2020036654号-1
                </a>
                <img :src="policeIcon" class="filing-img" alt="" />
                <span>京公网安备 11030102011597 号</span>
              </div>
            </div>
          </div>
          <div class="footer-right">
            <div class="code-box">
              <div
                v-for="(item, index) in footerCodeList"
                :key="index"
                class="code-pop"
              >
                <img :src="item.img" class="code-img" alt="" />
                <div class="code-layer">
                  <img :src="item.code" alt="" />
                  <p class="txt">{{ item.label }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </ContentWrapper>
    </div>
  </div>
</template>

<style lang="scss" scoped>
$color: #fff;

.footer {
  overflow: hidden;
  background: #121214;
  margin-top: 72px;

  :deep(.content-wrapper) {
    padding-bottom: 0;
  }

  .atom {
    text-align: center;
    padding-top: 24px;
    position: relative;

    .atom-text {
      color: $color;
      @include h4;
    }
    a {
      display: inline-block;
    }
    .atom-logo {
      height: 32px;
      margin-top: 12px;
    }
  }

  .footer-content {
    background: var(--footer-bg) no-repeat bottom center;
    background-size: cover;
    @include tip1;

    .quick-nav {
      margin: 16px auto 0;
      display: flex;
      justify-content: space-between;
      max-width: 1140px;

      .category {
        .category-title {
          color: var(--o-color-white);
          @include h4;
        }
        .navs {
          display: flex;
          flex-direction: column;
          .nav {
            margin-top: 8px;
            @include tip1;
            a {
              color: rgba(255, 255, 255, 0.6);
              @include hover {
                color: rgba(255, 255, 255, 1);
              }
            }
          }
          .nav:first-child {
            margin-top: 10px;
          }
        }
      }
    }

    .friendship-link {
      margin-top: 16px;
      padding-bottom: 12px;
      display: flex;
      border-bottom: 1px solid rgba(229, 229, 229, 0.12);
      @include tip2;

      .friendship-link-title {
        color: var(--o-color-white);
        margin-right: 38px;
      }
      .friendship-link-item {
        white-space: nowrap;
        color: rgba(255, 255, 255, 0.6);
        &:not(:last-of-type) {
          margin-right: 24px;
        }
        @include hover {
          color: rgba(255, 255, 255, 1);
        }
      }
    }

    .inner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 0 32px;
      position: relative;
    }
  }

  .footer-logo {
    flex: 1;
    img {
      height: 46px;
    }
    .show-pc {
      display: block;
    }
    .show-mo {
      display: none;
    }
  }

  .footer-option {
    text-align: center;
    @include tip1;

    .link {
      color: $color;
      display: inline-block;
    }
    .footer-option-item {
      align-items: center;
    }

    .footer-info {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: var(--o-gap-4);
      margin-top: 8px;
    }

    .copyright-text {
      color: rgba(255, 255, 255, 0.6);
      white-space: nowrap;
    }

    .copyright {
      display: flex;
      align-items: center;
      gap: var(--o-gap-2);
      color: rgba(255, 255, 255, 0.6);

      .filing-link {
        color: rgba(255, 255, 255, 0.6);
        @include hover {
          color: rgba(255, 255, 255, 1);
        }
      }
      .filing-img {
        height: 16px;
        width: 16px;
        align-self: center;
      }
    }
  }

  .license {
    color: $color;
    margin-top: 6px;
    span {
      color: rgba(255, 255, 255, 0.6);
    }
  }

  .footer-right {
    flex: 1;
    .code-box {
      display: flex;
      justify-content: right;
      gap: 16px;
      .code-pop {
        cursor: pointer;
        position: relative;
        height: 20px;
        display: block;
        > img {
          height: 100%;
          object-fit: cover;
        }
        .code-layer {
          position: absolute;
          top: -105px;
          left: -32px;
          z-index: 99;
          display: none;
          background: #fff;
          padding: 6px;
          img {
            width: 78px;
            height: 78px;
          }
          .txt {
            margin-top: 8px;
            color: $color;
            display: none;
          }
          &::after {
            border: 10px solid transparent;
            content: '';
            border-top-color: #fff;
            position: absolute;
            bottom: -20px;
            left: 50%;
            transform: translateX(-50%);
            display: block;
          }
        }
        @include hover {
          .code-layer {
            display: block;
          }
        }
      }
    }
  }

  .email {
    color: $color;
  }
}
</style>
