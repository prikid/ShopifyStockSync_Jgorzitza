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
          <b-button v-if="log_group_id && !processStarted" @click="downloadLogCsv" label="Download CSV log"
                    type="is-primary"/>
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
        <b-button icon-left="check"
                  icon-pack="fas"
                  :type="props.row.active ? 'is-success' : 'is-dark'"
                  class="is-inverted is-shadowless"
                  style="background: none"
                  @click="toggleActive(props.row)"
        />

      </b-table-column>

      <b-table-column v-slot="props">
        <div class="buttons is-pulled-right">
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

export default {
  // TODO pagination

  name: 'Dashboard',
  components: {LogViewer},
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
      log_group_id: undefined
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

    downloadLogCsv() {
      const url = `/api/logs/download-csv/${this.log_group_id}`
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
          .then(({data}) => {
                this.writeToLog(data.logs)

                if (data.complete) {
                  // console.log(data)

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
            this.writeToLog(err)
            if (err instanceof AxiosError && ["ERR_NETWORK", "ERR_TIMED_OUT", "ERR_NETWORK_IO_SUSPENDED", "ERR_NETWORK_CHANGED"].includes(err.code)) {
              setTimeout(this.checkProgress, 5000);
            }
          });
    },

    syncNow(row, dry = false) {
      const endpoint = dry ? 'dryrun' : 'run'
      // const endpoint = 'testlog'
      const url = `/api/sources/${row.id}/${endpoint}/`;

      this.is_log_modal_open = true
      this.processStarted = true
      this.logRowsCounter = 0

      axios.post(url)
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
