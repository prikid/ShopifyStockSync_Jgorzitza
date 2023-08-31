<template>
  <div id="app" class="hero is-fullheight">
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
        <b-navbar-item>
          <router-link to="/dashboard">Dashboard</router-link>
        </b-navbar-item>
      </template>

      <template #end>
        <template v-if="$store.getters.isAuthenticated">

          <b-navbar-item>
            <router-link to="/unmatched_review">Review unmatched</router-link>
          </b-navbar-item>

          <b-navbar-item>
            <router-link to="/logs">Logs</router-link>
          </b-navbar-item>
        </template>

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

    <section class="section">
      <router-view/>
    </section>

    <footer class="footer is-flex-align-items-flex-end mt-auto">
      <small class="is-pulled-right">
        <span>Copyright ©2023</span>
      </small>
    </footer>

  </div>
</template>

<script>
import LoginForm from "@/components/LoginForm.vue";

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
