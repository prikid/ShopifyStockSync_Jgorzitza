<template>
  <div id="app">
    <section class="hero is-fullheight">
      <div class="hero-head">
        <b-navbar>
          <template #brand>
            <b-navbar-item tag="router-link" :to="{ path: '/' }">
              <img
                  src="https://cdn.shopify.com/s/files/1/0289/7212/2147/files/OneguylogotransparentBG_ca79c89e-b8f4-42aa-bafb-563233510a38.png"
                  alt="OneGuyGarage products and orders sync"
              >
            </b-navbar-item>
          </template>
          <template #start>
            <!--        <b-navbar-item href="/">Home</b-navbar-item>-->
          </template>

          <template #end>
            <b-navbar-item tag="div">

              <b-button v-if="!$store.getters.isAuthenticated" @click="isLoginModalActive = true">Log in</b-button>
              <b-button v-else @click="logout">Logout</b-button>
            </b-navbar-item>
          </template>
        </b-navbar>

        <b-modal
            v-model="isLoginModalActive"
            has-modal-card
            trap-focus
            :destroy-on-hide="false"
            aria-role="dialog"
            aria-label="Login"
            close-button-aria-label="Close"
            aria-modal
        >
          <template #default="props">
            <login-form
                :is-modal-mode="true"
                @close="isLoginModalActive=false"
                @authenticated="on_authenticated"
                @authentication_error="on_authentication_error"
            />
          </template>
        </b-modal>
      </div>
      <div class="hero-body">
        <router-view/>
      </div>

      <div class="hero-foot">
        <footer class="footer">
          <small class="is-pulled-right">
            <span>Copyright ©2023</span>
          </small>
        </footer>

      </div>
    </section>
  </div>
</template>

<script>
import LoginForm from "@/components/LoginForm.vue";
import axios from 'axios'
import store from "@/store";

export default {
  name: 'Home',
  components: {
    LoginForm
  },

  data() {
    return {
      isLoginModalActive: false,
    }
  },

  methods: {
    on_authenticated() {
      this.isLoginModalActive = false
      const toPath = this.$route.query.to || '/dashboard';
      this.$router.push(toPath);
    },

    on_authentication_error(e) {
      console.log(e);
      this.$buefy.toast.open({
        duration: 5000,
        message: e.message,
        position: 'is-bottom',
        type: 'is-danger'
      })
    },

    logout() {
      this.$store.commit('removeToken')
      this.$router.push("/", () => {
      })
    }
  }
}
</script>


<style lang="scss">
</style>
