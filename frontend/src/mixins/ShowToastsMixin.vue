<script>

export default {
  name: "ShowToastsMixin",

  methods: {
   showErrorToast(error, message) {
      this.$buefy.toast.open({
        duration: 5000,
        message: message,
        position: 'is-bottom',
        type: 'is-danger'
      });

      console.log(error);
    },
  }
}
</script>
