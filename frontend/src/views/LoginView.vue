<template>
  <div class="column is-4 is-offset-4">
    <login-form
        @authenticated="on_authenticated"
        @authentication_error="on_authentication_error"
    />
  </div>

</template>

<script>
import LoginForm from "@/components/LoginForm.vue";

export default {
  name: 'LoginView',

  components: {
    LoginForm
  },

  methods: {
    on_authenticated() {
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
    }
  }
}

</script>