<template>
  <div>
    <b-loading :is-full-page="true" v-model="isLoading" :can-cancel="false"></b-loading>
    <vue-csv-import
        ref="vue_csv_import"
        url="/api/upload-custom-csv/"
        :autoMatchFields="true"
        :autoMatchIgnoreCase="true"
        :headers="true"
        :canIgnore="true"
        :shopify-locations="shopifyLocations"

        @input="before_uploading"
        @addToSchedulerEvent="addToScheduler"
        :callback="on_success"
        :catch="on_failure"
        :finally="on_finally"

        :mandatory-fields="['barcode', 'sku']"

        submitBtnText="Upload & Sync"
        submitBtnClass="button is-primary"

        submitDryBtnText="Upload & Dry run"
        submitDryBtnClass="button is-secondary"

        buttonClass="button ml-2"
        tableClass="table"
        tableSelectClass="select"
    >
    </vue-csv-import>
  </div>

</template>

<script>

import VueCsvImport from "@/components/VueCsvImport.vue";
import axios from "axios";
import showToastsMixin from "@/mixins/ShowToastsMixin.vue";

export default {
  name: 'UploadCustomCsv',
  components: {VueCsvImport},
  mixins: [showToastsMixin],

  props: {
    shopifyLocations: Array
  },

  data: () => ({
    isLoading: false
  }),

  methods: {
    saveNewCSVSource(source_name, params) {
      axios.post('api/sources/', {
        name: source_name,
        active: true,
        processor: 'CustomCSVProcessor',
        params: params
      })
          .then(() => {
            this.$emit('newSourceCreated');
            this.$refs.vue_csv_import.resetFileSelector();
          })
          .catch(axios_error => {
            this.showErrorToast(axios_error, axios_error.message);
          })
    },

    addToScheduler(params) {

      this.$buefy.dialog.prompt({
        message: `Give a name`,
        inputAttrs: {
          placeholder: 'e.g. New supplier CSV',
          maxlength: 30
        },
        trapFocus: true,
        onConfirm: source_name => this.saveNewCSVSource(source_name, params)
      })


    },

    before_uploading() {
      this.isLoading = true;
    },
    on_success(response, dry, updatePrice, updateInventory, shopifyInventoryLocation) {
      this.$emit("input", response.data.custom_csv_id, dry, updatePrice, updateInventory, shopifyInventoryLocation);
    },
    on_failure(axios_error) {
      this.showErrorToast(error, axios_error.response.data.error || 'Something went wrong')
    },
    on_finally() {
      this.isLoading = false;
    }
  }
}
</script>
