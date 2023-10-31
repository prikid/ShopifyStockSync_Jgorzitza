<template>
  <div class="vue-csv-uploader">
    <b-loading :is-full-page="true" v-model="isLoading" :can-cancel="false"></b-loading>

    <div class="form">
      <div class="vue-csv-uploader-part-one" v-if="!sample">
        <div class="form-check form-group csv-import-checkbox" v-if="headers === null">
          <slot name="hasHeaders" :headers="hasHeaders" :toggle="toggleHasHeaders">
            <input
                :class="checkboxClass" type="checkbox"
                :id="makeId('hasHeaders')"
                :value="hasHeaders"
                @change="toggleHasHeaders"
            />
            <label class="form-check-label" :for="makeId('hasHeaders')">
              File Has Headers
            </label>
          </slot>
        </div>

        <b-field grouped>
          <b-input type="url" v-model="csv_url" ref="csv_url" placeholder="Enter CSV file url" expanded></b-input>
          <p class="control">
            <b-button :disabled="!is_csv_url_valid" class="button" @click="loadFromUrl">Next</b-button>
          </p>
        </b-field>

        <label>OR</label>

        <b-field grouped class="mt-2">
          <div class="file has-name ">
            <label class="file-label">
              <input ref="csv" type="file" @change.prevent="validFileMimeType" class="file-input" name="csv"/>
              <span class="file-cta">
                <span class="file-icon">
                  <i class="fas fa-upload"></i>
                </span>
                <span class="file-label">Choose a file…</span>
              </span>
              <span v-if="isValidFileMimeType" class="file-name" v-text="filename"/>
            </label>
          </div>

          <slot name="error" v-if="showErrorMessage">
            <p class="help is-danger">
              File type is invalid
            </p>
          </slot>

          <!--          <slot name="next" :load="load">-->
          <!--            <button type="submit" v-if="!disabledNextButton" :class="buttonClass" @click.prevent="load">-->
          <!--              {{ loadBtnText }}-->
          <!--            </button>-->
          <!--          </slot>-->
        </b-field>
      </div>
      <div class="vue-csv-uploader-part-two">
        <div class="vue-csv-mapping box" v-if="sample">
          <b-button @click="resetFileSelector" icon-left="xmark" type="is-white" class="is-pulled-right"/>
          <h2 class="my-2 subtitle">Fields mapping</h2>
          <table :class="tableClass">
            <slot name="thead">
              <thead>
              <tr>
                <th>Field</th>
                <th>CSV Column</th>
              </tr>
              </thead>
            </slot>
            <tbody>
            <tr v-for="(field, key) in fieldsToMap" :key="key">
              <td>{{ field.label }}</td>
              <td>
                <select
                    :class="tableSelectClass"
                    :name="`csv_uploader_map_${key}`"
                    v-model="map[field.key]"
                >
                  <option :value="null" v-if="canIgnore">Ignore</option>
                  <option v-for="(column, key) in firstRow" :key="key" :value="key">
                    {{ column }}
                  </option>
                </select>
              </td>
            </tr>
            </tbody>
          </table>
          <p class="help is-danger my-2" v-if="fieldIsMandatoryText">{{ fieldIsMandatoryText }}</p>
          <div class="block">
            <b-checkbox v-model="updatePrice">Update price</b-checkbox>
            <b-checkbox v-model="updateInventory">Update inventory</b-checkbox>
            <b-select v-model="shopifyInventoryLocationIdx">
              <option v-for="(locationName, key) in shopifyLocations" :value="key" :key="key">
                {{ locationName }}
              </option>
            </b-select>
          </div>
          <div class="form-group mt-2" v-if="url">
            <slot name="submit" :submit="submit">
              <div class="buttons">
                <input type="submit" :class="submitDryBtnClass" @click.prevent="submit(true)"
                       :value="submitDryBtnText"/>
                <input type="submit" :class="submitBtnClass" @click.prevent="submit(false)" :value="submitBtnText"/>
                <b-button :disabled="!is_csv_url_valid" @click="addToScheduler" type="is-light">Add to scheduler
                </b-button>
              </div>
            </slot>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import {drop, every, forEach, get, isArray, isUndefined, map, set} from "lodash";
import axios from "axios";
import Papa from "papaparse";
import mimeTypes from "mime-types";

export default {

  props: {
    value: Array,
    url: {
      type: String,
    },
    mapFields: {
      type: Object,
      default: () => ({
        'barcode': 'barcode',
        'sku': 'sku',
        'price': 'price',
        'inventory_quantity': 'inventory_quantity',
        'location_name': 'location_name'
      })
    },

    shopifyLocations: Array,

    mandatoryFields: {
      type: Array,
      default: () => ([]),
    },

    callback: {
      type: Function,
      default: () => ({}),
    },
    catch: {
      type: Function,
      default: () => ({}),
    },
    finally: {
      type: Function,
      default: () => ({}),
    },
    parseConfig: {
      type: Object,
      default() {
        return {};
      },
    },
    headers: {
      default: null,
    },
    loadBtnText: {
      type: String,
      default: "Next",
    },
    submitBtnText: {
      type: String,
      default: "Submit",
    },
    submitDryBtnText: {
      type: String,
      default: "Submit Dry",
    },
    submitBtnClass: {
      type: String,
      default: "btn btn-primary",
    },
    submitDryBtnClass: {
      type: String,
      default: "btn btn-secondary",
    },
    autoMatchFields: {
      type: Boolean,
      default: false,
    },
    autoMatchIgnoreCase: {
      type: Boolean,
      default: false,
    },
    tableClass: {
      type: String,
      default: "table",
    },
    checkboxClass: {
      type: String,
      default: "form-check-input",
    },
    buttonClass: {
      type: String,
      default: "btn btn-primary",
    },
    inputClass: {
      type: String,
      default: "form-control-file",
    },
    validation: {
      type: Boolean,
      default: true,
    },
    fileMimeTypes: {
      type: Array,
      default: () => {
        return ["text/csv", "text/x-csv", "application/vnd.ms-excel", "text/plain"];
      },
    },
    tableSelectClass: {
      type: String,
      default: "form-control",
    },
    canIgnore: {
      type: Boolean,
      default: false,
    },

  },

  data: () => ({
    isLoading: false,
    form: {
      csv: null,
    },
    fieldsToMap: [],
    map: {},
    hasHeaders: true,
    csv: null,
    csv_url: '',
    sample: null,
    isValidFileMimeType: false,
    fileSelected: false,

    updatePrice: true,
    updateInventory: true,
    shopifyInventoryLocationIdx: 0,

    fieldIsMandatoryText: ''

  }),

  created() {
    this.initializeFromProps();
  },


  methods: {
    resetFileSelector() {
      this.sample = null;
      this.csv_url = ''
      this.csv = null;
      this.isValidFileMimeType = false;
      this.fileSelected = false;
      this.form.csv = null;

    },

    addToScheduler() {
      let fields_map = {}

      try {
        forEach(this.map, (column, field) => {
          if (this.mandatoryFields.includes(field) && column === null)
            throw new Error(`The field ${field} is mandatory`);

          fields_map[field] = this.csv[0][column]
        });

        this.verify_input_fields(fields_map);

      } catch (e) {
        this.fieldIsMandatoryText = e.message;
        return false;
      }


      this.$emit(
          'addToSchedulerEvent',
          {
            csv_url: this.csv_url,
            update_price: this.updatePrice,
            update_inventory: this.updateInventory,
            shopify_inventory_location: this.shopifyLocations[this.shopifyInventoryLocationIdx],
            fields_map: fields_map,
          })
    },

    initializeFromProps() {
      this.hasHeaders = this.headers;

      if (isArray(this.mapFields)) {
        this.fieldsToMap = map(this.mapFields, (item) => {
          return {
            key: item,
            label: item,
          };
        });
      } else {
        this.fieldsToMap = map(this.mapFields, (label, key) => {
          return {
            key: key,
            label: label,
          };
        });
      }
    },

    submit(dry = false) {
      const _this = this;
      try {
        this.form.csv = this.buildMappedCsv();
      } catch (e) {
        this.fieldIsMandatoryText = e.message;
        return false;
      }

      this.$emit("input", this.form.csv, dry, this.updatePrice, this.updateInventory);


      if (this.url) {
        axios
            .post(this.url, this.form, {timeout: 60000})
            .then((response) => {
              _this.callback(response, dry, this.updatePrice, this.updateInventory, this.shopifyLocations[this.shopifyInventoryLocationIdx]);
            })
            .catch((response) => {
              _this.catch(response, dry);
            })
            .finally((response) => {
              this.resetFileSelector();
              _this.finally(response, dry);
            });
      } else {
        _this.callback(this.form.csv, dry);
      }
    },

    buildMappedCsv() {
      const _this = this;
      this.fieldIsMandatoryText = '';

      let csv = this.hasHeaders ? drop(this.csv) : this.csv;

      return map(csv, (row) => {
        let newRow = {};

        forEach(_this.map, (column, field) => {
          if (_this.mandatoryFields.includes(field) && column === null)
            throw new Error(`The field ${field} is mandatory`);

          set(newRow, field, get(row, column));
        });

        this.verify_input_fields(newRow);

        return newRow;
      });
    },

    verify_input_fields(item) {
      if (!this.updatePrice && !this.updateInventory)
        throw new Error(`Check at least one option: update price or update inventory`);

      if (this.updatePrice && isUndefined(item.price))
        throw new Error(`The price field is required for prices updating`);

      if (this.updateInventory && isUndefined(item.inventory_quantity))
        throw new Error(`The inventory_quantity field is required for prices updating`);
    },


    validFileMimeType() {
      let file = this.$refs.csv.files[0];
      const mimeType = file.type === "" ? mimeTypes.lookup(file.name) : file.type;

      if (file) {
        this.fileSelected = true;
        this.isValidFileMimeType = this.validation ? this.validateMimeType(mimeType) : true;
      } else {
        this.isValidFileMimeType = !this.validation;
        this.fileSelected = false;
      }

      if (this.isValidFileMimeType)
        this.load();
    },

    validateMimeType(type) {
      return this.fileMimeTypes.indexOf(type) > -1;
    },

    showUnableToLoadFileToast(error) {
      this.showErrorToast(error, `Unable to load the file`);
    },

    load() {
      this.readLocalFile(this.afterFileLoaded);
    },

    loadFromUrl(row) {
      if (this.$refs.csv_url.checkHtml5Validity())
        this.readFileByURL(this.afterFileLoaded);

    },

    afterFileLoaded(output) {
      const _this = this;

      _this.sample = get(Papa.parse(output, {preview: 2, skipEmptyLines: true}), "data");
      _this.csv = get(Papa.parse(output, {skipEmptyLines: true}), "data");
    },

    readLocalFile(callback) {
      let file = this.$refs.csv.files[0];

      if (file) {
        let reader = new FileReader();
        reader.readAsText(file, "UTF-8");
        reader.onload = function (evt) {
          callback(evt.target.result);
        };
        reader.onerror = function (error) {
          this.showUnableToLoadFileToast(error)
        }
      }
    },

    readFileByURL(callback) {
      this.isLoading = true;

      axios
          .post('api/get_csv_proxy/', {csv_url: this.csv_url})
          .then((response) => {
            callback(response.data);
          })
          .catch((error) => {
            this.showUnableToLoadFileToast(error)
          })
          .finally(() => {
            this.isLoading = false;
          });
    },

    toggleHasHeaders() {
      this.hasHeaders = !this.hasHeaders;
    },

    makeId(id) {
      return `${id}${this._uid}`;
    },

  },
  watch: {
    map: {
      deep: true,
      handler: function (newVal) {
        if (!this.url) {
          let hasAllKeys = Array.isArray(this.mapFields)
              ? every(this.mapFields, function (item) {
                return Object.prototype.hasOwnProperty.call(newVal, item);
              })
              : every(this.mapFields, function (item, key) {
                return Object.prototype.hasOwnProperty.call(newVal, key);
              });

          if (hasAllKeys) {
            this.submit();
          }
        }
      },
    },
    sample(newVal) {
      if (this.autoMatchFields) {
        if (newVal !== null) {
          this.fieldsToMap.forEach((field) => {
            newVal[0].forEach((columnName, index) => {
              if (this.autoMatchIgnoreCase === true) {
                if (field.label.toLowerCase().trim() === columnName.toLowerCase().trim()) {
                  this.$set(this.map, field.key, index);
                }
              } else {
                if (field.label.trim() === columnName.trim()) {
                  this.$set(this.map, field.key, index);
                }
              }
            });
          });
        }
      }
    },
    mapFields() {
      this.initializeFromProps();
    }
  },
  computed: {
    is_csv_url_valid() {
      const urlRegex = /^\s*(http|https|ftp):\/\/[^\s/$.?#].[^\s]*\.(csv|txt|tsv)\??.*$/i;
      return urlRegex.test(this.csv_url);
    },

    filename() {
      try {
        return this.$refs.csv.files[0].name;
      } catch (e) {
      }

      return '';
    },

    firstRow() {
      return get(this, "sample.0");
    },
    showErrorMessage() {
      return this.fileSelected && !this.isValidFileMimeType;
    },
    disabledNextButton() {
      return !this.isValidFileMimeType;
    },
  },
};
</script>
