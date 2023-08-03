<template>
  <div class="container">
    <b-modal v-model="is_log_modal_open" :has-modal-card="true" :can-cancel="false" :full-screen="true">

      <div class="modal-card">
        <header class="modal-card-head">
          <p class="modal-card-title text-center">Synchronization process log</p>
        </header>
        <section class="modal-card-body">
          <log-viewer :log="log" :hasNumber="false"/>
        </section>
        <footer class="modal-card-foot">
          <b-button @click="onButtonClick" :label="buttonLabel" :disabled="isButtonDisabled"/>
          <b-button v-if="log_group_id && !processStarted" @click="downloadLogCsv(true)" label="Download matched CSV"
                    type="is-primary"/>
          <b-button v-if="log_group_id && !processStarted" @click="downloadLogCsv(false)" label="Download unmatched CSV"
                    type="is-secondary"/>
        </footer>
      </div>
    </b-modal>

    <b-table
        :data="sources"
        :loading="loading"
    >
      <b-table-column field="name" label="Name" v-slot="props">
        {{ props.row.name }}
        <!--        <router-link to="logs">{{ props.row.name }}</router-link>-->
      </b-table-column>

      <b-table-column field="active" label="Run hourly" v-slot="props" centered>
        <b-button v-if="props.row.processor!=='CustomCSVProcessor'"
                  icon-left="check"
                  icon-pack="fas"
                  :type="props.row.active ? 'is-success' : 'is-dark'"
                  class="is-inverted is-shadowless"
                  style="background: none"
                  @click="toggleActive(props.row)"
        />

      </b-table-column>

      <b-table-column v-slot="props">
        <template v-if="props.row.processor==='CustomCSVProcessor'">
          <upload-custom-csv
              @input="(csv_id, dry, updatePrice, updateInventory) =>
              customCsvSync(props.row, dry, csv_id, updatePrice, updateInventory)"
          ></upload-custom-csv>
        </template>

        <div v-else class="buttons">
          <b-button @click="syncNow(props.row, true)" label="Dry run" type="is-secondary"/>
          <b-button @click="syncNow(props.row, false)" label="Sync now" type="is-primary"/>
        </div>
      </b-table-column>
    </b-table>
  </div>
</template>

<script>
import axios, {AxiosError} from 'axios'
import LogViewer from "@femessage/log-viewer/src/log-viewer.vue";
import DownloadFileMixin from "@/mixins/DownloadFileMixin.vue";
import UploadCustomCsv from "@/views/UploadCustomCsv.vue";

export default {
  // TODO pagination

  name: 'Dashboard',
  components: {UploadCustomCsv, LogViewer},
  mixins: [DownloadFileMixin],

  data() {
    return {
      loading: false,
      sources: [],
      is_log_modal_open: false,
      processStarted: false,
      taskId: undefined,
      log: '',
      logRowsCounter: 0,
      isButtonDisabled: false,
      log_group_id: undefined,
    }
  },

  mounted() {
    this.getDataSources()
  },

  computed: {
    buttonLabel() {
      return this.processStarted ? 'Stop' : 'Close'
    }
  },

  methods: {

    customCsvSync(row, dry, custom_csv_data_id, updatePrice, updateInventory) {
      this.syncNow(row, dry, {
        custom_csv_data_id: custom_csv_data_id,
        update_price: updatePrice,
        update_inventory: updateInventory,
      })
    },

    downloadLogCsv(only_matched) {
      const url = `/api/products_sync_logs/download-csv/${this.log_group_id}/${+only_matched}`
      this.downloadFile(url)
    },

    toggleActive(row) {
      axios.patch(`/api/sources/${row.id}/`, {'active': !row.active})
          .then(({data}) => {
            row.active = data['active']
          })
    },

    onButtonClick() {
      if (this.processStarted)
        this.stopProcess()
      else {
        this.clearLog()
        this.is_log_modal_open = false
      }
    },

    stopProcess() {
      axios.delete(`/api/task/${this.taskId}/`)
          .then(({data}) => {
            this.writeToLog("Stopping the process ...")
            this.log_group_id = data.gid
            this.isButtonDisabled = true
          })
    },

    clearLog() {
      this.logRowsCounter = 0
      this.log = ''
    },

    writeToLog(rows) {
      if (typeof rows === 'string')
        rows = [rows]

      if (Array.isArray(rows) && rows.length) {
        this.logRowsCounter += rows.length
        const msg = rows.join('\n')
        this.log += msg + "\n"
      }
    },

    checkProgress() {
      axios.get(`/api/task/${this.taskId}/${this.logRowsCounter}`)
          .then((response) => {
                const data = response.data;
                this.writeToLog(data.logs);

                if (data.complete) {
                  this.log_group_id = data.gid
                  this.isButtonDisabled = false
                  this.processStarted = false
                  this.writeToLog('--Done--')
                } else {
                  setTimeout(this.checkProgress, 500);
                }
              }
          )
          .catch((err) => {
            console.log(err);
            this.writeToLog(err.message + ": " + err.response.statusText + "; " + err.response.data['err_message'])
            if (err instanceof AxiosError && ["ERR_NETWORK", "ERR_TIMED_OUT", "ERR_NETWORK_IO_SUSPENDED", "ERR_NETWORK_CHANGED"].includes(err.code)) {
              setTimeout(this.checkProgress, 5000);
            } else {
              this.isButtonDisabled = false
              this.processStarted = false
              this.writeToLog('The process has been interrupted')
            }
          });
    },

    syncNow(row, dry = false, queryParams) {
      const endpoint = dry ? 'dryrun' : 'run'
      const url = new URL(process.env.VUE_APP_BACKEND_HOST || window.location.origin);
      url.pathname = `/api/sources/${row.id}/${endpoint}/`;

      for (const key in queryParams) {
        url.searchParams.append(key, queryParams[key]);
      }

      this.is_log_modal_open = true
      this.processStarted = true
      this.logRowsCounter = 0

      axios.post(url.toString())
          .then(({data}) => {
            this.taskId = data.task_id;
            setTimeout(this.checkProgress, 500);
          })
          .catch((err) =>
              console.log(err)
          );
    },

    async getDataSources() {
      this.loading = true
      axios.get('/api/sources/?limit=100')
          .then(({data}) => {
            this.sources = data.results
            this.loading = false
          })
          .catch((error) => {
            this.sources = []
            this.loading = false
            throw error
          })
    }
  }
}

</script>
